const assert = require("assert");
const _ = require("lodash");

// Test-only lodash usage — should be classified as non-production by NotSudo
describe("merge", () => {
  it("merges objects", () => {
    const out = _.merge({ a: 1 }, { b: 2 });
    assert.strictEqual(out.a, 1);
    assert.strictEqual(out.b, 2);
  });
});
