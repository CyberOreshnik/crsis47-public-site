const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

(async () => {
  const html = fs.readFileSync("source-hub/index.html", "utf8");
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const handlers = {};
  function element(id) {
    return {
      value: "", hidden: false, textContent: "",
      addEventListener(event, handler) { handlers[id + event] = handler; },
      replaceChildren() {}, append() {}
    };
  }
  const elements = Object.fromEntries(
    ["search","type","lens","count","results","first","next","filters"].map(id => [id, element(id)])
  );
  const location = {href: "https://example.org/source-hub/?q=evidence", search: "?q=evidence"};
  const requested = [];
  let offline = false;
  const history = {
    pushState(_, __, url) { location.href = url.href; location.search = url.search; }
  };
  vm.runInNewContext(script, {
    document: {
      querySelector: () => ({content: "https://search.example.org/"}),
      getElementById: id => elements[id],
      createElement: () => element("")
    },
    window: {addEventListener: (key, handler) => { handlers[key] = handler; }},
    fetch: async url => {
      requested.push(url);
      if (offline) throw new Error("offline");
      return {ok:true, json:async () => ({items:[],nextCursor:"signed-cursor"})};
    },
    URL, URLSearchParams, AbortController, location, history
  });
  await new Promise(setImmediate);
  assert.equal(requested[0].searchParams.get("q"), "evidence");
  assert.equal(requested[0].searchParams.get("limit"), "25");
  handlers.nextclick();
  await new Promise(setImmediate);
  assert.equal(requested[1].searchParams.get("cursor"), "signed-cursor");
  assert.match(location.search, /cursor=/);
  location.href = "https://example.org/source-hub/?q=evidence";
  location.search = "?q=evidence";
  await handlers.popstate();
  assert.equal(requested[2].searchParams.has("cursor"), false);
  assert.equal(elements.search.value, "evidence");
  offline = true;
  location.search = "?q=evidence";
  await handlers.popstate();
  await new Promise(setImmediate);
  assert.match(elements.count.textContent, /Offline venue preview only/);
  assert.equal(elements.next.hidden, true);
  location.search = "?q=evidence&project=unknown";
  await handlers.popstate();
  await new Promise(setImmediate);
  assert.match(elements.count.textContent, /cannot apply these filters/);
  console.log("PASS: navigation, offline preview, advanced-filter fail closed");
})().catch(error => { console.error(error); process.exitCode = 1; });
