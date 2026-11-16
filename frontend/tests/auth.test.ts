import assert from "node:assert/strict";
import test from "node:test";
import { canAccessRoute, displayNameFromLogin, parseStoredUser } from "../src/authTypes.ts";
const user = {id:"hiring-team",name:"Hiring team",email:"hiring-team",role:"recruiter",title:"Recruiter",organization:"",readOnly:false};
test("only recruiter sessions may be restored; local student identities are not accounts", () => {
  assert.deepEqual(parseStoredUser(JSON.stringify(user)), user);
  assert.equal(parseStoredUser(JSON.stringify({...user,role:"student"})),null);
  assert.equal(parseStoredUser(JSON.stringify({...user,role:"admin"})),null);
  assert.equal(parseStoredUser("{"),null);
});
test("recruiter data is not accessible in a student or anonymous view", () => {
  for (const role of [null,"student"] as const) for (const path of ["/recruiter","/recruiter/one/evidence","/placement"]) assert.equal(canAccessRoute(path,role),false);
  assert.equal(canAccessRoute("/placement","recruiter"),true);
  assert.equal(canAccessRoute("/student",null),true);
  assert.equal(displayNameFromLogin("hiring.team"),"hiring team");
});
