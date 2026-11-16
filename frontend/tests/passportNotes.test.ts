import assert from "node:assert/strict";
import test from "node:test";
import {
  GROWTH_UNAVAILABLE,
  growthUnavailable,
  growthUnavailableMessage,
  kitUnavailable,
} from "../src/passportNotes.ts";
import type { Passport } from "../src/api.ts";

function stubPassport(overrides: Partial<Passport> = {}): Passport {
  return {
    id: "test-passport",
    created_at: "2026-10-25T12:00:00Z",
    github_username: "test-user",
    target_role: "Backend Developer Intern",
    sources: { repos: 1, resume: true, certificates: 0 },
    skills: [],
    rejected_claims: [],
    role_match: {
      role_id: "backend-intern",
      role_name: "Backend Developer Intern",
      met: 2,
      total: 8,
      requirements: [],
    },
    growth_tasks: [],
    interview_kit: [],
    is_demo: false,
    ...overrides,
  };
}

test("growthUnavailableMessage surfaces generation_warning when present", () => {
  const warning = "The growth plan could not be generated this time (GEMINI_API_KEY is not configured).";
  const passport = stubPassport({ generation_warning: warning });
  assert.equal(growthUnavailable(passport), true);
  assert.equal(growthUnavailableMessage(passport), warning);
});

test("growthUnavailableMessage surfaces generation_error when present", () => {
  const passport = stubPassport({ generation_error: "QuotaExceeded" });
  assert.equal(growthUnavailable(passport), true);
  assert.match(growthUnavailableMessage(passport), /QuotaExceeded/);
});

test("growthUnavailableMessage explains demo candidates without repositories", () => {
  const passport = stubPassport({ is_demo: true, sources: { repos: 0, resume: true, certificates: 0 } });
  assert.equal(growthUnavailable(passport), true);
  assert.match(growthUnavailableMessage(passport), /no repository attached/i);
});

test("growthUnavailableMessage returns default message for standard gap without error", () => {
  const passport = stubPassport({ sources: { repos: 2, resume: true, certificates: 0 } });
  assert.equal(growthUnavailable(passport), true);
  assert.equal(growthUnavailableMessage(passport), GROWTH_UNAVAILABLE);
});

test("growthUnavailable returns false when growth tasks are present", () => {
  const passport = stubPassport({
    growth_tasks: [{ skill_id: "docker", target_repo: "demo", task: "Add Dockerfile", evidence_it_will_create: "Config" }],
  });
  assert.equal(growthUnavailable(passport), false);
});

test("kitUnavailable returns true when code-backed skills exist but kit is empty", () => {
  const passport = stubPassport({
    skills: [{ skill_id: "python", name: "Python", level: "Applied", certified: false, evidence: [] }],
  });
  assert.equal(kitUnavailable(passport), true);
});
