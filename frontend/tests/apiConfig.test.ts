import assert from "node:assert/strict";
import test from "node:test";
import { resolveApiBase } from "../src/apiConfig.ts";

test("uses the configured backend URL and removes trailing slashes", () => {
  assert.equal(resolveApiBase(" https://api.example.test/ ", false), "https://api.example.test");
});

test("uses localhost only for an unconfigured development build", () => {
  assert.equal(resolveApiBase(undefined, true), "http://localhost:8000");
});

test("leaves an unconfigured production build without a backend URL", () => {
  assert.equal(resolveApiBase(undefined, false), "");
  assert.equal(resolveApiBase("  ", false), "");
});
