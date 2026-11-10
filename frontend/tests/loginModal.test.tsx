import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { act, create } from "react-test-renderer";
import LoginModal from "../src/components/LoginModal";
import { AuthProvider } from "../src/auth";

test("clicking the recruiter demo fills both fields and leaves sign-in to the user", async () => {
  const previousDocument = globalThis.document;
  const previousHTMLElement = globalThis.HTMLElement;
  Object.defineProperty(globalThis, "HTMLElement", {
    configurable: true,
    value: class HTMLElement {},
  });
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: {
      activeElement: null,
      addEventListener() {},
      removeEventListener() {},
    },
  });

  let renderer: ReturnType<typeof create> | undefined;
  try {
    await act(async () => {
      renderer = create(
        <AuthProvider>
          <LoginModal />
        </AuthProvider>,
      );
    });

    await act(async () => {
      renderer!.root.findByProps({ id: "demo-fill-recruiter" }).props.onClick();
    });

    assert.equal(renderer.root.findByProps({ id: "auth-email" }).props.value, "recruiter@techcorp.com");
    assert.equal(renderer.root.findByProps({ id: "auth-password" }).props.value, "recruiter2026");
    assert.match(
      renderer.root.findByProps({ role: "status" }).findAllByType("strong").map((node) => node.children.join("")).join(" "),
      /Demo recruiter credentials.*Sign in/,
    );
    assert.match(
      renderer.root.findByProps({ id: "demo-fill-recruiter" }).props.className,
      /auth-demo-card-selected/,
    );
    assert.equal(renderer.root.findByProps({ id: "auth-submit-btn" }).props.disabled, false);
  } finally {
    if (renderer) {
      await act(async () => {
        renderer!.unmount();
      });
    }
    if (previousDocument === undefined) {
      delete (globalThis as { document?: Document }).document;
    } else {
      Object.defineProperty(globalThis, "document", { configurable: true, value: previousDocument });
    }
    if (previousHTMLElement === undefined) {
      delete (globalThis as { HTMLElement?: typeof HTMLElement }).HTMLElement;
    } else {
      Object.defineProperty(globalThis, "HTMLElement", { configurable: true, value: previousHTMLElement });
    }
  }
});
