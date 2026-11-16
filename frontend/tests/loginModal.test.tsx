import assert from "node:assert/strict";
import test from "node:test";
import React from "react";
import { act, create } from "react-test-renderer";
import LoginModal from "../src/components/LoginModal";
import { AuthProvider, useAuth } from "../src/auth";
function OpenSignIn() { const {openLoginModal}=useAuth(); return <button onClick={openLoginModal}>Open</button>; }
test("first visit is usable without a fabricated account; recruiter sign-in contains no public credentials", async () => {
 const previous=globalThis.document;
 const previousElement=globalThis.HTMLElement;
 Object.defineProperty(globalThis,"HTMLElement",{configurable:true,value:class HTMLElement {}});
 Object.defineProperty(globalThis,"document",{configurable:true,value:{activeElement:null,body:{style:{overflow:""}},addEventListener(){},removeEventListener(){}}});
 let renderer:ReturnType<typeof create>;
 try {
  await act(async()=>{renderer=create(<AuthProvider><OpenSignIn/><LoginModal/></AuthProvider>);});
  assert.equal(renderer!.root.findAllByProps({role:"dialog"}).length,0);
  await act(async()=>{renderer!.root.findByType("button").props.onClick();});
  const tree=JSON.stringify(renderer!.toJSON());
  assert.match(tree,/Recruiter sign-in/);
  assert.doesNotMatch(tree,/recruiter2026|student2026|techcorp|Demo|Jordan|Alex Vance/);
  assert.equal(renderer!.root.findByProps({id:"auth-password"}).props.value,"");
 } finally { await act(async()=>renderer?.unmount()); Object.defineProperty(globalThis,"document",{configurable:true,value:previous}); Object.defineProperty(globalThis,"HTMLElement",{configurable:true,value:previousElement}); }
});
