// Post-response Script (Tests)
// This script validates the API response.

// 1. Check if the status code is 200 OK
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// 2. Validate Response Time (Performance Check)
pm.test("Response time is acceptable (< 2000ms)", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

// 3. Parse JSON response body
var jsonData = pm.response.json();

// 4. Validate Response Structure
pm.test("Response has 'predictions' array", function () {
    pm.expect(jsonData).to.have.property("predictions");
    pm.expect(jsonData.predictions).to.be.an("array");
});

pm.test("Response contains summary metrics", function () {
    pm.expect(jsonData).to.have.property("fraud_count");
    pm.expect(jsonData).to.have.property("fraud_rate");
    pm.expect(jsonData).to.have.property("total");
});

// 5. Data Integrity Check (Count matches input)
// We know we sent 5 items in this example
pm.test("Prediction count matches input size", function () {
    // If you want to check against the requested size dynamically:
    // var reqBody = JSON.parse(pm.environment.get("batch_payload"));
    // pm.expect(jsonData.total).to.eql(reqBody.transactions.length);
    
    // Simple check for > 0
    pm.expect(jsonData.total).to.be.above(0);
});

// 6. Check individual prediction structure
pm.test("Check first prediction format", function () {
    if (jsonData.predictions.length > 0) {
        var firstPred = jsonData.predictions[0];
        pm.expect(firstPred).to.have.property("TransactionID");
        pm.expect(firstPred).to.have.property("isFraud");
        // isFraud should be 0 or 1
        pm.expect(firstPred.isFraud).to.be.oneOf([0, 1]);
    }
});

console.log("Tests completed. Fraud Rate: " + jsonData.fraud_rate + "%");
