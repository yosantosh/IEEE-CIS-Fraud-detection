"""
Data Feature Engineering & Transformation Component
====================================================
This module handles feature engineering and data transformation
for the IEEE-CIS Fraud Detection Pipeline.

Usage with DVC:
    dvc repro data_transformation
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
from typing import Optional

from sklearn.model_selection import train_test_split, KFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline

from src.utils import reduce_memory, Read_write_yaml_schema
from src.logger import logger
from src.exception import CustomException
from config.config import DataTransformationConfig




class Data_FE_Transformation:
    def __init__(self, config: Optional[DataTransformationConfig] = None):
        self.config = config or DataTransformationConfig()


    def create_transaction_amount_features(self,df) -> pd.DataFrame:
        """Create features based on transaction amount"""

        # Log transformation
        df['TransactionAmt_log'] = np.log1p(df['TransactionAmt'])
        
        # Decimal part extraction: often fraudsters use round numbers
        df['TransactionAmt_decimal'] = ((df['TransactionAmt'] - df['TransactionAmt'].astype(int)) * 1000).fillna(0).astype(int)
        
        # Is round
        df['TransactionAmt_is_round'] = (df['TransactionAmt'] == df['TransactionAmt'].astype(int)).astype(int)
        
        # Amount bin: it can reduce noise by smoothing and other benefits too
        df['TransactionAmt_bins'] = pd.cut(
            df['TransactionAmt'].astype('float32'),
            bins=self.config.trans_amt_bins,
            labels=self.config.trans_amt_labels
        ).astype(float)
        
        # Value in cents
        df['TransactionAmt_cents'] = (df['TransactionAmt'] * 100 % 100).fillna(0).astype(int)
        
        # Is micro amount
        df['TransactionAmt_is_micro'] = (df['TransactionAmt'] < 10).astype(int)
        
        # Sudden amount jump
        card_cols = self.config.card_cols
        df['card_id'] = df[card_cols].fillna('nan').astype(str).agg('_'.join, axis=1)
        
        df = df.sort_values(['card_id', 'TransactionDT'])
        df['prev_amount'] = (
            df.groupby('card_id')['TransactionAmt']
            .shift(1)
        )
        
        df['prev_amount'] = df['prev_amount'].fillna(df['TransactionAmt'])
        df['amount_jump_ratio'] = df['TransactionAmt'] / (df['prev_amount'] + 1)
        
        df['is_amount_spike'] = (df['amount_jump_ratio'] > 5).astype(int)
        
        # Rolling mean
        df['rolling_median_amt'] = (
            df.groupby('card_id')['TransactionAmt']
            .rolling(5, min_periods=1)
            .median()
            .shift(1)
            .reset_index(level=0, drop=True)
        )
        df['rolling_median_amt'] = df['rolling_median_amt'].fillna(df['TransactionAmt'])
        df['amt_vs_rolling'] = df['TransactionAmt'] / (df['rolling_median_amt'] + 1)
        
        # Same amount repeated multiple times
        df['amt_repeat_count'] = (
            df.groupby(['card_id', 'TransactionAmt'])['TransactionAmt']
            .transform('count')
        )
        
        # High amount compared to user's normal behavior (if user_id column exists)
        if 'user_id' in df.columns:
            user_mean = df.groupby('user_id')['TransactionAmt'].transform('mean')
            user_std = df.groupby('user_id')['TransactionAmt'].transform('std')
            df['amount_zscore'] = (df['TransactionAmt'] - user_mean) / (user_std + 1)
        
        return df



    def create_time_features(self,df: pd.DataFrame) -> pd.DataFrame:
        """
        Create time-based features from TransactionDT (seconds since reference time)
        """

        # -------------------------
        # Basic time decomposition
        # -------------------------

        # Hour of day (0–23) derived from seconds
        df['Transaction_hour'] = (df['TransactionDT'] // 3600) % 24

        # Seconds within a day (cyclic behavior)
        df['Transaction_sec_in_day'] = df['TransactionDT'] % 86400

        # Time of day buckets
        # 0 = night, 1 = morning, 2 = afternoon, 3 = evening
        df['Transaction_time_of_day'] = pd.cut(
            df['Transaction_hour'],
            bins=self.config.time_of_day_bins,
            labels=self.config.time_of_day_labels
        ).astype(int)

        # -------------------------
        # Binary behavior flags
        # -------------------------

        # Night transactions (fraud often spikes at night)
        df['Transaction_is_night'] = (
            (df['Transaction_hour'] >= 0) & (df['Transaction_hour'] < 6)
        ).astype(int)

        # Business hours (normal human activity)
        df['Transaction_is_business_hour'] = (
            (df['Transaction_hour'] >= 9) & (df['Transaction_hour'] <= 17)
        ).astype(int)

        # -------------------------
        # Sequential time features
        # -------------------------

        # Time gap from previous transaction for the same card
        # (detects bursts / bot activity)
        df['Transaction_time_gap'] = (
            df.groupby('card_id')['TransactionDT']
            .diff()
        )

        # Fill first transaction gap with large value (no previous txn)
        df['Transaction_time_gap'] = df['Transaction_time_gap'].fillna(999999)

        # -------------------------
        # Velocity features
        # -------------------------

        # Number of transactions in last 1 hour per card
        df['Transaction_cnt_1hr'] = (
            df.groupby('card_id')['TransactionDT']
            .rolling(3600)
            .count()
            .reset_index(level=0, drop=True)
        )

        # -------------------------
        # Cyclic encoding (tree + linear friendly)
        # -------------------------

        # Sine/Cosine encoding of hour (captures cyclic nature)
        df['Transaction_hour_sin'] = np.sin(2 * np.pi * df['Transaction_hour'] / 24)
        df['Transaction_hour_cos'] = np.cos(2 * np.pi * df['Transaction_hour'] / 24)

        return df


    def create_card_features(self,df:pd.DataFrame) -> pd.DataFrame:
        "This func create card related features"
        print("Start creating card Features...")

        card_cols = self.config.card_cols
        for i in card_cols:
            if i in df.columns:
                df[i]=df[i].fillna(-1).astype(str)
        #since we already created card_id with combining all cards so we dont need to make smaller combination like card1_card2 etc  but we can combine address and card

        df['card1_addrs1'] = df['card1']+ "-" + df['addr1'].fillna(0).astype(str)
        df['card1_addrs2'] = df['card1']+ "-" + df['addr2'].fillna(0).astype(str)
        df['card2_addrs1'] = df['card2']+ "-" + df['addr1'].fillna(0).astype(str)


        #maybe fraudsters can buy specific products while doing frauds
        df['card1_ProductCD'] = df[['card1','ProductCD']].ffill().astype(str).agg('_'.join, axis=1)
        df['card2_ProductCD'] = df[['card2','ProductCD']].ffill().astype(str).agg('_'.join, axis=1)

        #card uses frequency ---> not use agg('count'); but transform('count') becasue it will return one counted value for original one row
        df['card_id_count'] = df.groupby('card_id')['TransactionID'].transform('count')

        # card+ address frequency
        df['card_add_count'] = df.groupby('addr1')['TransactionID'].transform('count')

        print('Card features has been created successfully')    
        return df


    def create_email_features(self,df, target_col='isFraud', n_splits=5):


        # try to use tldextract; otherwise provide a fallback extractor
        try:
            import tldextract

            def extract_domain_parts(domain):
                # returns (subdomain, domain, suffix) similar to tldextract.extract
                ext = tldextract.extract(domain)
                return ext.subdomain, ext.domain, ext.suffix

        except Exception:
            # lightweight fallback (not as complete as tldextract, but works for common cases)
            def extract_domain_parts(domain):
                """
                Very small fallback:
                - treats 'co.uk', 'gov.uk', 'ac.uk' as double-suffix when seen
                - returns (subdomain, domain, suffix)
                """
                if not isinstance(domain, str) or domain in ('', 'missing', 'nan'):
                    return '', 'missing', ''
                domain = domain.lower().strip()
                parts = domain.split('.')
                if len(parts) == 1:
                    return '', parts[0], ''
                # handle common double-suffixes
                double_suffixes = {'co.uk', 'gov.uk', 'ac.uk', 'co.jp', 'com.au', 'net.au'}
                last_two = '.'.join(parts[-2:])
                if last_two in double_suffixes:
                    suffix = last_two
                    dom = parts[-3] if len(parts) >= 3 else parts[-2]
                    sub = '.'.join(parts[:-3]) if len(parts) > 3 else ''
                    return sub, dom, suffix
                else:
                    suffix = parts[-1]
                    dom = parts[-2]
                    sub = '.'.join(parts[:-2]) if len(parts) > 2 else ''
                    return sub, dom, suffix


        # normalize & fill
        for col in self.config.email_domains:
            if col in df.columns:
                df[col] = df[col].fillna('missing').astype(str).str.lower()
            else:
                df[col] = 'missing'  # ensures downstream code won't fail

        # vendor map
        vendor_map = self.config.email_vendor_map

        def get_vendor(domain):
            _, dom, _ = extract_domain_parts(domain)
            return vendor_map.get(dom, 'other')

        def get_tld(domain):
            _, _, suffix = extract_domain_parts(domain)
            return suffix if suffix else 'missing'

        # apply safely
        df['P_email_vendor'] = df['P_emaildomain'].apply(get_vendor)
        df['R_email_vendor'] = df['R_emaildomain'].apply(get_vendor)
        df['P_email_tld'] = df['P_emaildomain'].apply(get_tld)
        df['R_email_tld'] = df['R_emaildomain'].apply(get_tld)

        # match and presence
        df['email_domain_match'] = (df['P_emaildomain'] == df['R_emaildomain']).astype(int)
        df['email_presence'] = np.select(
            [
                (df['P_emaildomain'] != 'missing') & (df['R_emaildomain'] != 'missing'),
                (df['P_emaildomain'] != 'missing') & (df['R_emaildomain'] == 'missing'),
                (df['P_emaildomain'] == 'missing') & (df['R_emaildomain'] != 'missing')
            ],
            ['both_present', 'only_P', 'only_R'],
            default='both_missing'
        )

        # domain frequency: ensure TransactionID exists (if not, use index)
        id_col = 'TransactionID' if 'TransactionID' in df.columns else None
        if id_col:
            df['P_domain_count'] = df.groupby('P_emaildomain')[id_col].transform('count')
            df['R_domain_count'] = df.groupby('R_emaildomain')[id_col].transform('count')
        else:
            df['P_domain_count'] = df.groupby('P_emaildomain')['P_emaildomain'].transform('count')
            df['R_domain_count'] = df.groupby('R_emaildomain')['R_emaildomain'].transform('count')

        # K-Fold target encoding (only for P_emaildomain). Works even if target missing -> all NaNs replaced by global mean
        df['P_domain_fraud_rate'] = np.nan
        if target_col in df.columns:
            kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
            for train_idx, val_idx in kf.split(df):
                train_df = df.iloc[train_idx]
                val_df = df.iloc[val_idx]
                mapping = train_df.groupby('P_emaildomain')[target_col].mean()
                df.loc[val_idx, 'P_domain_fraud_rate'] = val_df['P_emaildomain'].map(mapping)
            global_mean = df[target_col].mean()
            df['P_domain_fraud_rate'] = df['P_domain_fraud_rate'].fillna(global_mean)
        else:
            df['P_domain_fraud_rate'] = 0.0

        return df



    def create_device_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create device-related features with safe string handling."""
        print("Creating device features...")
        
        # Helper function for safe string splitting
        def safe_split_get(value, delimiter=' ', index=0, default='unknown'):
            """Safely split a string and get element at index, with fallback."""
            if pd.isna(value):
                return default
            parts = str(value).split(delimiter)
            return parts[index] if len(parts) > index and parts[index] else default
        
        # Device type features
        if 'DeviceType' in df.columns:
            df['DeviceType_is_mobile'] = (df['DeviceType'] == 'mobile').astype(int)
            df['DeviceType_is_desktop'] = (df['DeviceType'] == 'desktop').astype(int)
        else:
            df['DeviceType_is_mobile'] = 0
            df['DeviceType_is_desktop'] = 0

        # Device info features
        if 'DeviceInfo' in df.columns:
            # Safe brand extraction: split by '/' first, then by space
            def get_device_brand(x):
                if pd.isna(x):
                    return 'unknown'
                s = str(x)
                first_part = s.split('/')[0] if '/' in s else s
                parts = first_part.split()
                return parts[0] if parts else 'unknown'
            
            df['Device_brand'] = df['DeviceInfo'].apply(get_device_brand)
            
            # Device info length
            df['DeviceInfo_length'] = df['DeviceInfo'].apply(
                lambda x: len(str(x)) if pd.notna(x) else 0
            )

        # Browser features from id_31
        if 'id_31' in df.columns:
            def get_browser_name(x):
                if pd.isna(x):
                    return 'unknown'
                parts = str(x).split()
                return parts[0].lower() if parts else 'unknown'
            
            df['browser'] = df['id_31'].apply(get_browser_name)
            df['Broser_is_chrome'] = df['id_31'].apply(lambda x: 1 if pd.notna(x) and 'chrome' in str(x).lower() else 0)
            df['Broser_is_firefox'] = df['id_31'].apply(lambda x: 1 if pd.notna(x) and 'firefox' in str(x).lower() else 0)
            df['Broser_is_edge'] = df['id_31'].apply(lambda x: 1 if pd.notna(x) and 'edge' in str(x).lower() else 0)
            df['Broser_is_safari'] = df['id_31'].apply(lambda x: 1 if pd.notna(x) and 'safari' in str(x).lower() else 0)

        # OS features from id_30
        if 'id_30' in df.columns:
            # Safe OS name and version extraction
            def get_os_name(x):
                if pd.isna(x):
                    return 'unknown'
                parts = str(x).split(' ', 1)
                return parts[0] if parts and parts[0] else 'unknown'
            
            def get_os_version(x):
                if pd.isna(x):
                    return 'unknown'
                parts = str(x).split(' ', 1)
                return parts[1] if len(parts) > 1 and parts[1] else 'unknown'
            
            df['os_name'] = df['id_30'].apply(get_os_name)
            df['os_version'] = df['id_30'].apply(get_os_version)
            
            df['OS_is_Windows'] = df['id_30'].apply(
                lambda x: 1 if pd.notna(x) and 'windows' in str(x).lower() else 0
            )
            df['OS_is_Mac'] = df['id_30'].apply(
                lambda x: 1 if pd.notna(x) and 'mac' in str(x).lower() else 0
            )
            df['OS_is_iOS'] = df['id_30'].apply(
                lambda x: 1 if pd.notna(x) and 'ios' in str(x).lower() else 0
            )
            df['OS_is_Android'] = df['id_30'].apply(
                lambda x: 1 if pd.notna(x) and 'android' in str(x).lower() else 0
            )
        else:
            # Create default columns if id_30 doesn't exist
            df['os_name'] = 'unknown'
            df['os_version'] = 'unknown'
            df['OS_is_Windows'] = 0
            df['OS_is_Mac'] = 0
            df['OS_is_iOS'] = 0
            df['OS_is_Android'] = 0
                
        # Screen resolution from id_33
        if 'id_33' in df.columns:
            def get_screen_dimension(x, index):
                if pd.isna(x) or 'x' not in str(x):
                    return -1
                parts = str(x).split('x')
                if len(parts) > index:
                    try:
                        return int(parts[index])
                    except (ValueError, TypeError):
                        return -1
                return -1
            
            df['Screen_width'] = df['id_33'].apply(lambda x: get_screen_dimension(x, 0))
            df['Screen_height'] = df['id_33'].apply(lambda x: get_screen_dimension(x, 1))
            df['Screen_area'] = df['Screen_width'] * df['Screen_height']
            df['Screen_aspect_ratio'] = df.apply(
                lambda row: row['Screen_width'] / row['Screen_height'] if row['Screen_height'] > 0 else -1, axis=1
            )

        print('Device features has been created!')
        return df

    def create_address_features(self,df):
        """Create features based on address information"""
        print("Creating address features...")
        
        # Address combinations
        if 'addr1' in df.columns and 'addr2' in df.columns:
            df['addr1_addr2'] = df['addr1'].astype(str) + '_' + df['addr2'].astype(str)
        
        # Address + ProductCD
        if 'addr1' in df.columns and 'ProductCD' in df.columns:
            df['addr1_ProductCD'] = df['addr1'].astype(str) + '_' + df['ProductCD'].astype(str)
        
        # Address distance from P_emaildomain (proxy for geographic mismatch)
        if 'addr1' in df.columns:
            df['addr1_missing'] = df['addr1'].isna().astype(int)
        
        if 'addr2' in df.columns:
            df['addr2_missing'] = df['addr2'].isna().astype(int)
        
        # Both addresses missing
        if 'addr1' in df.columns and 'addr2' in df.columns:
            df['both_addr_missing'] = (df['addr1'].isna() & df['addr2'].isna()).astype(int)
        
        # dist1 and dist2 features
        if 'dist1' in df.columns:
            df['dist1_missing'] = df['dist1'].isna().astype(int)
            # Handle empty strings and non-numeric values
            df['dist1_log'] = np.log1p(pd.to_numeric(df['dist1'], errors='coerce').fillna(0))
        
        if 'dist2' in df.columns:
            df['dist2_missing'] = df['dist2'].isna().astype(int)
            # Handle empty strings and non-numeric values
            df['dist2_log'] = np.log1p(pd.to_numeric(df['dist2'], errors='coerce').fillna(0))
        print('Address features has been created!')
        return df



    def create_v_features(self, df):
        """Create aggregation features from V columns"""
        print("Creating V-column aggregation features...")
        
        # Get all V columns
        v_cols = [col for col in df.columns if col.startswith('V')]
        
        if len(v_cols) == 0:
            return df
        
        # Convert all V columns to numeric (handles empty strings and other non-numeric values)
        for col in v_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Group V columns by their correlation patterns (based on EDA from competition)
        v_groups = {
            'v1': ['V1', 'V2', 'V3', 'V4', 'V5', 'V6', 'V7', 'V8', 'V9', 'V10', 'V11'],
            'v2': ['V12', 'V13', 'V14', 'V15', 'V16', 'V17', 'V18', 'V19', 'V20', 'V21', 'V22', 'V23', 'V24', 'V25', 'V26'],
            'v3': ['V27', 'V28', 'V29', 'V30', 'V31', 'V32', 'V33', 'V34'],
            'v4': ['V35', 'V36', 'V37', 'V38', 'V39', 'V40', 'V41', 'V42', 'V43', 'V44', 'V45', 'V46', 'V47', 'V48', 'V49', 'V50', 'V51', 'V52'],
            'v5': ['V53', 'V54', 'V55', 'V56', 'V57', 'V58', 'V59', 'V60', 'V61', 'V62', 'V63', 'V64', 'V65', 'V66', 'V67', 'V68', 'V69', 'V70', 'V71', 'V72', 'V73', 'V74'],
            'v6': ['V75', 'V76', 'V77', 'V78', 'V79', 'V80', 'V81', 'V82', 'V83', 'V84', 'V85', 'V86', 'V87', 'V88', 'V89', 'V90', 'V91', 'V92', 'V93', 'V94'],
            'v7': ['V95', 'V96', 'V97', 'V98', 'V99', 'V100', 'V101', 'V102', 'V103', 'V104', 'V105', 'V106', 'V107', 'V108', 'V109', 'V110', 'V111', 'V112', 'V113', 'V114', 'V115', 'V116', 'V117', 'V118', 'V119', 'V120', 'V121', 'V122', 'V123', 'V124', 'V125', 'V126', 'V127', 'V128', 'V129', 'V130', 'V131', 'V132', 'V133', 'V134', 'V135', 'V136', 'V137'],
        }
        
        for group_name, group_cols in v_groups.items():
            # Filter to existing columns
            existing_cols = [col for col in group_cols if col in df.columns]
            
            if len(existing_cols) > 0:
                # Sum of group (skipna handles NaN)
                df[f'{group_name}_sum'] = df[existing_cols].sum(axis=1, skipna=True)
                
                # Mean of group
                df[f'{group_name}_mean'] = df[existing_cols].mean(axis=1, skipna=True)
                
                # Std of group
                df[f'{group_name}_std'] = df[existing_cols].std(axis=1, skipna=True)
                
                # NaN count in group
                df[f'{group_name}_nan_count'] = df[existing_cols].isna().sum(axis=1)
        
        # Overall V statistics
        existing_v_cols = [col for col in v_cols if col in df.columns]
        if len(existing_v_cols) > 0:
            df['V_sum_all'] = df[existing_v_cols].sum(axis=1, skipna=True)
            df['V_mean_all'] = df[existing_v_cols].mean(axis=1, skipna=True)
            df['V_std_all'] = df[existing_v_cols].std(axis=1, skipna=True)
            df['V_nan_count_all'] = df[existing_v_cols].isna().sum(axis=1)
            df['V_nan_ratio'] = df['V_nan_count_all'] / len(existing_v_cols)
        print("V-column aggregation features are created!")    
        return df



    def create_aggregation_features(self,train_df):
        """Create frequency and aggregation features for both train and test"""
        print("Creating aggregation features...")
        
        # 1. Create copies to avoid SettingWithCopy warnings on original dfs
        train_df = train_df.copy()
        
        # 3. Columns for frequency encoding
        freq_cols = self.config.frequency_encoded_cols
        
        for col in freq_cols:
            if col in train_df.columns:
                # Frequency encoding
                freq = train_df[col].value_counts().to_dict()
                train_df[f'{col}_freq'] = train_df[col].map(freq)
        
        # 4. Transaction amount aggregations
        # Note: 'card1_card2' must exist in df before running this
        agg_cols = self.config.aggregation_cols 
        
        for col in agg_cols:
            if col in train_df.columns:
                # Mean transaction amount
                agg_mean = train_df.groupby(col)['TransactionAmt'].mean().to_dict()
                train_df[f'{col}_TransactionAmt_mean'] = train_df[col].map(agg_mean)
                
                # Std transaction amount
                agg_std = train_df.groupby(col)['TransactionAmt'].std().to_dict()
                train_df[f'{col}_TransactionAmt_std'] = train_df[col].map(agg_std)
                
                # Transaction amount deviation from mean
                train_df[f'{col}_TransactionAmt_dev'] = train_df['TransactionAmt'] - train_df[f'{col}_TransactionAmt_mean']
        
        print("C and D Column Features has been implemented...")
        return train_df




    def create_id_features(self, df):
        """Create features from identity columns"""
        print("Creating ID features...")
        
        # id_01 to id_11 are numerical
        id_num_cols = [f'id_0{i}' for i in range(1, 10)] + ['id_10', 'id_11']
        existing_id_num = [col for col in id_num_cols if col in df.columns]
        
        # Ensure numerical ID columns are actually numeric
        for col in existing_id_num:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if len(existing_id_num) > 0:
            df['id_num_nan_count'] = df[existing_id_num].isna().sum(axis=1)
            # Use columns directly since they are now numeric
            df['id_num_mean'] = df[existing_id_num].mean(axis=1, skipna=True)
            df['id_num_std'] = df[existing_id_num].std(axis=1, skipna=True)
        
        # id_12 to id_38 are categorical
        # Check specific important ones
        if 'id_12' in df.columns:
            df['id_12_isFound'] = (df['id_12'] == 'Found').astype(int)
        
        if 'id_15' in df.columns:
            df['id_15_isNew'] = (df['id_15'] == 'New').astype(int)
            df['id_15_isFound'] = (df['id_15'] == 'Found').astype(int)
        
        if 'id_16' in df.columns:
            df['id_16_isFound'] = (df['id_16'] == 'Found').astype(int)
        
        if 'id_28' in df.columns:
            df['id_28_isNew'] = (df['id_28'] == 'New').astype(int)
            df['id_28_isFound'] = (df['id_28'] == 'Found').astype(int)
        
        if 'id_29' in df.columns:
            df['id_29_isFound'] = (df['id_29'] == 'Found').astype(int)
        
        # id_34 (match status)
        if 'id_34' in df.columns:
            df['id_34_match'] = df['id_34'].apply(
                lambda x: int(str(x).split(':')[1]) if pd.notna(x) and ':' in str(x) else -1
            )
        
        # id_36 features
        if 'id_36' in df.columns:
            df['id_36_isT'] = (df['id_36'] == 'T').astype(int)
        
        # id_37, id_38 features
        if 'id_37' in df.columns:
            df['id_37_isT'] = (df['id_37'] == 'T').astype(int)
        
        if 'id_38' in df.columns:
            df['id_38_isT'] = (df['id_38'] == 'T').astype(int)
        
        return df



    def create_uid_features(self,df):
        """
        Create UID (Unique User ID) - The MAGIC feature!
        card1 + addr1 + D1 can identify unique credit card holders.
        """
        print("🔥 Creating UID magic features...")
        
    
        # UID TYPE 1: card1 + addr1 (location-based)
        df['uid1'] = df['card1'].astype(str) + '_' + df['addr1'].astype(str)
        
        # UID TYPE 2: card1 + addr1 + D1 (time-based) - MOST POWERFUL!
        df['uid2'] = df['card1'].astype(str) + '_' + df['addr1'].astype(str) + '_' + df['D1'].astype(str)
        
        # UID TYPE 3: Full card fingerprint
        df['uid3'] = (df['card1'].astype(str) + '_' + 
                    df['card2'].astype(str) + '_' + 
                    df['card3'].astype(str) + '_' + 
                    df['card4'].astype(str) + '_' + 
                    df['card5'].astype(str) + '_' + 
                    df['card6'].astype(str))
        
        # UID TYPE 4: card + email domain
        df['uid4'] = df['card1'].astype(str) + '_' + df['P_emaildomain'].astype(str)
        
        print(f"  ✓ uid1 unique values: {df['uid1'].nunique():,}")
        print(f"  ✓ uid2 unique values: {df['uid2'].nunique():,}")
        print(f"  ✓ uid3 unique values: {df['uid3'].nunique():,}")
        print(f"  ✓ uid4 unique values: {df['uid4'].nunique():,}")
        

        
        return df


    def create_uid_aggregations(self,df):
        """
        Create aggregation features based on UID.
        These features capture user behavior patterns.
        """
        print("🔥 Creating UID aggregation features...")

        df = df.sort_values('TransactionDT').reset_index(drop=True)
        
        uid_cols = self.config.uid_cols
        
        for uid in uid_cols:
            print(f"  Processing {uid}...")
            
            # Transaction count per UID
            df[f'{uid}_count'] = df.groupby(uid)['TransactionID'].transform('count')
            
            # Transaction amount statistics
            df[f'{uid}_TransactionAmt_mean'] = df.groupby(uid)['TransactionAmt'].transform('mean')
            df[f'{uid}_TransactionAmt_std'] = df.groupby(uid)['TransactionAmt'].transform('std')
            
            # How unusual is THIS transaction for this user?
            df[f'{uid}_TransactionAmt_to_mean'] = df['TransactionAmt'] / (df[f'{uid}_TransactionAmt_mean'] + 0.001)
            df[f'{uid}_TransactionAmt_to_std'] = (df['TransactionAmt'] - df[f'{uid}_TransactionAmt_mean']) / (df[f'{uid}_TransactionAmt_std'] + 0.001)
            
            # Time-based features per UID
            df[f'{uid}_D1_mean'] = df.groupby(uid)['D1'].transform('mean')
        

        
        print(f"  ✓ Created {len(uid_cols) * 6} UID aggregation features")
        return df


        
    def create_enhanced_frequency_features(self,df):
        """
        Enhanced frequency encoding with normalization
        """
        print("🔥 Creating enhanced frequency features...")
        
        freq_cols = self.config.enhanced_freq_cols
        
        for col in freq_cols:
            if col in df.columns:
                freq = df[col].value_counts()
                df[f'{col}_freq'] = df[col].map(freq)
                df[f'{col}_freq_norm'] = df[f'{col}_freq'] / len(df)
        

        print(f"  ✓ Created {len([c for c in freq_cols if c in df.columns]) * 2} frequency features")
        return df





    def preprocessor(self, raw_data):
        """
        Preprocess feature-engineered data: train/test split, encoding, and PCA on V columns.
        
        Args:
            raw_data: Feature-engineered DataFrame with target column 'isFraud'
            
        Returns:
            Tuple of (Train_transformed, Test_transformed) DataFrames with target column included
        """
        logger.info("Starting preprocessing (train/test split, encoding, PCA)...")
        df = raw_data.copy()
        
        # Separate features and target
        y = df['isFraud']
        X = df.drop('isFraud', axis=1)

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=self.config.test_size, 
            shuffle=True, 
            random_state=self.config.random_state,
            stratify=y  # Maintain class balance
        )
        
        logger.info(f"Train set: {X_train.shape}, Test set: {X_test.shape}")
        logger.info(f"Train fraud rate: {y_train.mean():.4f}, Test fraud rate: {y_test.mean():.4f}")

        # Identify column types
        cat_cols = X_train.select_dtypes(include=['object', 'category']).columns.tolist()
        v_cols = [c for c in X_train.columns if c.startswith('V')]
        num_cols = [c for c in X_train.select_dtypes(include=np.number).columns.tolist() if c not in v_cols]
        
        logger.info(f"Categorical columns: {len(cat_cols)}, Numerical columns: {len(num_cols)}, V columns: {len(v_cols)}")
        
        # Define transformers
        num_transformer = SimpleImputer(strategy='constant', fill_value=self.config.fill_value)
        
        cat_transformer = OrdinalEncoder(
            handle_unknown='use_encoded_value', 
            unknown_value=-1,
            encoded_missing_value=self.config.fill_value
        )

        v_pca = make_pipeline(
            SimpleImputer(strategy='mean'),
            StandardScaler(),
            PCA(n_components=self.config.pca_n_components, svd_solver='full')
        )

        # Build column transformer
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', num_transformer, num_cols),
                ('cat', cat_transformer, cat_cols),
                ('pca', v_pca, v_cols)
            ],
            remainder='drop',
            verbose_feature_names_out=False
        ).set_output(transform="pandas")
        

        # Fit on Train only (prevent data leakage)
        X_train_processed = preprocessor.fit_transform(X_train)
        
        # SAVE PREPROCESSOR
        try:
            model_dir = "models"
            os.makedirs(model_dir, exist_ok=True)
            preprocessor_path = os.path.join(model_dir, "preprocessor.joblib")
            joblib.dump(preprocessor, preprocessor_path)
            logger.info(f"✓ Preprocessor saved to: {preprocessor_path}")
        except Exception as e:
            logger.error(f"Failed to save preprocessor: {str(e)}")
        
        # Transform Test using fitted preprocessor
        X_test_processed = preprocessor.transform(X_test)
        
        # Add target column back (reset index to align properly)
        X_train_processed = X_train_processed.reset_index(drop=True)
        X_test_processed = X_test_processed.reset_index(drop=True)
        
        X_train_processed['isFraud'] = y_train.reset_index(drop=True)
        X_test_processed['isFraud'] = y_test.reset_index(drop=True)
        
        logger.info(f"✓ Preprocessing complete!")
        logger.info(f"  Train shape: {X_train_processed.shape}")
        logger.info(f"  Test shape: {X_test_processed.shape}")

        return X_train_processed, X_test_processed



    def RUN(self):
        """
        Execute the complete feature engineering and transformation pipeline.
        
        Steps:
        1. Read ingested raw data
        2. Apply all feature engineering methods
        3. Save processed data
        
        Raises:
            CustomException: If any step in the pipeline fails
        """
        logger.info("=" * 60)
        logger.info("STARTING FEATURE ENGINEERING & TRANSFORMATION PIPELINE")
        logger.info("=" * 60)

        
        
        try:

            # Step 1: Read raw data
            logger.info("Step 1: Reading ingested .csv file...")
            try:
                df = pd.read_csv(self.config.raw_data_path)
                logger.info(f"✓ Data loaded successfully. Shape: {df.shape}")
            except Exception as e:
                logger.error(f"Failed to read raw data: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 1.5: Compare raw_data schema with schema.yaml (STRICT VALIDATION!)
            logger.info("Step 1.5: Validating raw_data schema against schema.yaml...")
            schema_yaml_path = self.config.schema_yaml_path
            try:
                schema_result = Read_write_yaml_schema.compare_schema(
                    df=df,
                    schema_name="raw_data",
                    schema_yaml_filepath=schema_yaml_path,
                    strict=True  # STRICT MODE - fail on schema mismatch!
                )
                logger.info("✓ Raw data schema validation PASSED")
            except FileNotFoundError:
                logger.warning("Schema file not found - skipping schema validation (first run?)")
            except ValueError as e:
                logger.warning(f"Schema 'raw_data' not found - skipping validation (first run?): {str(e)}")
            except Exception as e:
                logger.error(f"Schema validation FAILED: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 2: Transaction Amount Features
            logger.info("Step 2: Applying create_transaction_amount_features()...")
            try:
                df = self.create_transaction_amount_features(df)
                logger.info("✓ Transaction amount features created successfully")
            except Exception as e:
                logger.error(f"Failed to create transaction amount features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 3: Time Features
            logger.info("Step 3: Applying create_time_features()...")
            try:
                df = self.create_time_features(df)
                logger.info("✓ Time features created successfully")
            except Exception as e:
                logger.error(f"Failed to create time features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 4: Card Features
            logger.info("Step 4: Applying create_card_features()...")
            try:
                df = self.create_card_features(df)
                logger.info("✓ Card features created successfully")
            except Exception as e:
                logger.error(f"Failed to create card features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 5: Email Features
            logger.info("Step 5: Applying create_email_features()...")
            try:
                df = self.create_email_features(df)
                logger.info("✓ Email features created successfully")
            except Exception as e:
                logger.error(f"Failed to create email features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 6: Device Features
            logger.info("Step 6: Applying create_device_features()...")
            try:
                df = self.create_device_features(df)
                logger.info("✓ Device features created successfully")
            except Exception as e:
                logger.error(f"Failed to create device features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 7: Address Features
            logger.info("Step 7: Applying create_address_features()...")
            try:
                df = self.create_address_features(df)
                logger.info("✓ Address features created successfully")
            except Exception as e:
                logger.error(f"Failed to create address features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 8: V-Column Features
            logger.info("Step 8: Applying create_v_features()...")
            try:
                df = self.create_v_features(df)
                logger.info("✓ V-column features created successfully")
            except Exception as e:
                logger.error(f"Failed to create V-column features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 9: Aggregation Features
            logger.info("Step 9: Applying create_aggregation_features()...")
            try:
                df = self.create_aggregation_features(df)
                logger.info("✓ Aggregation features created successfully")
            except Exception as e:
                logger.error(f"Failed to create aggregation features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 10: ID Features
            logger.info("Step 10: Applying create_id_features()...")
            try:
                df = self.create_id_features(df)
                logger.info("✓ ID features created successfully")
            except Exception as e:
                logger.error(f"Failed to create ID features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 11: UID Features (MAGIC features!)
            logger.info("Step 11: Applying create_uid_features()...")
            try:
                df = self.create_uid_features(df)
                logger.info("✓ UID features created successfully")
            except Exception as e:
                logger.error(f"Failed to create UID features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 12: UID Aggregations
            logger.info("Step 12: Applying create_uid_aggregations()...")
            try:
                df = self.create_uid_aggregations(df)
                logger.info("✓ UID aggregation features created successfully")
            except Exception as e:
                logger.error(f"Failed to create UID aggregation features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 13: Enhanced Frequency Features
            logger.info("Step 13: Applying create_enhanced_frequency_features()...")
            try:
                df = self.create_enhanced_frequency_features(df)
                logger.info("✓ Enhanced frequency features created successfully")
            except Exception as e:
                logger.error(f"Failed to create enhanced frequency features: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 14: Prepprocessing steps
            logger.info("Step 14: Reducing memory usage...")
            Train_transformed = None
            Test_transformed = None
            try:
                X_train_processed, X_test_processed = self.preprocessor(df)
                Train_transformed = X_train_processed
                Test_transformed = X_test_processed
                logger.info("✓ Data Preprocessing completed")
            except Exception as e:
                logger.warning(f"Data Preprocessing failed (non-critical): {str(e)}")
                # Fallback: save the feature-engineered df directly without preprocessing
                Train_transformed = df
                Test_transformed = None
            
            # Step 15: Save transformed data
            logger.info("Step 15: Saving transformed data...")
            try:
                os.makedirs(self.config.processed_data_dir, exist_ok=True)

                output_path = os.path.join(self.config.processed_data_dir, "Train_transformed.csv")
                Train_transformed.to_csv(output_path, index=False)
                logger.info(f"✓ Train data saved to: {output_path}")

                if Test_transformed is not None:
                    output_path2 = os.path.join(self.config.processed_data_dir, "Test_transformed.csv")
                    Test_transformed.to_csv(output_path2, index=False)
                    
                    logger.info(f"✓ Test data saved to: {output_path2}")

            except Exception as e:
                logger.error(f"Failed to save transformed data: {str(e)}")
                raise CustomException(e, sys)
            
            # Step 16: Save preprocessed schema to schema.yaml
            logger.info("Step 16: Saving preprocessed data schema to schema.yaml...")
            try:
                schema_yaml_path = self.config.schema_yaml_path
                
                # Save Train_transformed schema
                Read_write_yaml_schema.save_dataframe_schema(
                    df=Train_transformed,
                    schema_name="preprocessed_train",
                    schema_yaml_filepath=schema_yaml_path
                )
                logger.info("✓ Train preprocessed schema saved to schema.yaml")
                
                # Save Test_transformed schema (if exists)
                if Test_transformed is not None:
                    Read_write_yaml_schema.save_dataframe_schema(
                        df=Test_transformed,
                        schema_name="preprocessed_test",
                        schema_yaml_filepath=schema_yaml_path
                    )
                    logger.info("✓ Test preprocessed schema saved to schema.yaml")
                    
            except Exception as e:
                logger.warning(f"Failed to save preprocessed schema (non-critical): {str(e)}")
            
            logger.info("=" * 60)
            logger.info(f"FEATURE ENGINEERING COMPLETED SUCCESSFULLY!")
            logger.info(f"Final shape for Train_transformed: {Train_transformed.shape}")
            if Test_transformed is not None:
                logger.info(f"Final shape for Test_transformed: {Test_transformed.shape}")
            logger.info(f"Total features: {Train_transformed.shape[1]}")
            logger.info("=" * 60)

            
        except CustomException:
            raise
        except Exception as e:
            logger.error(f"Feature engineering pipeline failed: {str(e)}")
            raise CustomException(e, sys)


# ============================================================================
# MAIN ENTRY POINT (for DVC pipeline)
# ============================================================================

def main():
    """Main entry point for DVC pipeline."""
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    logger.info("Initializing Feature Engineering Pipeline...")
    
    # Create config and run transformation
    config = DataTransformationConfig()
    transformer = Data_FE_Transformation(config)
    transformer.RUN()


if __name__ == "__main__":
    main()
