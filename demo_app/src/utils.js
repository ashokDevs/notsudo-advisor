const _ = require("lodash");

/** Utility used by production handlers — merges untrusted payloads. */
function deepMerge(target, source) {
  return _.merge(target, source);
}

function zipDefaults(obj) {
  return _.defaultsDeep({}, obj, { meta: { created: true } });
}

module.exports = { deepMerge, zipDefaults };
