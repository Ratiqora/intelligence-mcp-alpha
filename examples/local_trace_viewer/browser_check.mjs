// Optional Windows/Edge acceptance test; Node 22+ built-ins only.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {spawn, spawnSync} from "node:child_process";
import {pathToFileURL} from "node:url";

const [htmlFile, outputDirectory, browserPath] = process.argv.slice(2);
if (!htmlFile || !outputDirectory || !browserPath) {
  throw new Error("usage: node browser_check.mjs <generated-html> <output-dir> <edge-executable>");
}
fs.mkdirSync(outputDirectory, {recursive:true});
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "ratiqora-viewer-"));
const browser = spawn(browserPath, ["--headless=new","--disable-gpu","--no-first-run",
  "--disable-extensions","--disable-background-networking","--remote-debugging-port=0",
  "--remote-debugging-address=127.0.0.1","--user-data-dir="+profile,"about:blank"],
  {stdio:"ignore",windowsHide:true});
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
const evidence = {status:"INCOMPLETE",checks:[],page_errors:0,external_requests:0};
let socket, nextId=0;
const pending=new Map();
function check(condition,label){if(!condition)throw new Error(label);evidence.checks.push(label);}
function rpc(method,params={}){
  return new Promise((resolve,reject)=>{
    const id=++nextId;
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error("CDP timeout"));},8000);
    pending.set(id,{resolve,reject,timer});
    socket.send(JSON.stringify({id,method,params}));
  });
}
async function evaluate(expression){
  const response=await rpc("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
  if(response.exceptionDetails)throw new Error("page evaluation failed");
  return response.result.value;
}
async function waitPage(){
  for(let attempt=0;attempt<80;attempt++){
    if(await evaluate("document.readyState==='complete' && document.getElementById('detail-kind')?.textContent==='Insight'"))return;
    await delay(100);
  }
  throw new Error("page did not initialize");
}
async function clickNode(id,kind){
  const selector='#references button[data-node="'+id+'"]';
  const expression="(()=>{const b=document.querySelector("+JSON.stringify(selector)+");if(!b)return false;b.click();return document.getElementById('detail-kind').textContent==="+JSON.stringify(kind)+"})()";
  check(await evaluate(expression),"drill-down-"+id);
}
async function screenshot(name){
  const result=await rpc("Page.captureScreenshot",{format:"png",captureBeyondViewport:false});
  fs.writeFileSync(path.join(outputDirectory,name),Buffer.from(result.data,"base64"));
}
try{
  const portFile=path.join(profile,"DevToolsActivePort");
  for(let attempt=0;!fs.existsSync(portFile)&&attempt<200;attempt++)await delay(100);
  if(!fs.existsSync(portFile))throw new Error("browser startup timed out");
  const port=fs.readFileSync(portFile,"utf8").split(/\r?\n/)[0];
  const pages=await (await fetch("http://127.0.0.1:"+port+"/json/list")).json();
  const target=pages.find(page=>page.type==="page");
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true});});
  socket.addEventListener("message",event=>{
    const message=JSON.parse(event.data);
    if(message.id){
      const entry=pending.get(message.id);
      if(!entry)return;
      pending.delete(message.id);clearTimeout(entry.timer);
      if(message.error)entry.reject(new Error("CDP command failed"));else entry.resolve(message.result);
    }else if(message.method==="Runtime.exceptionThrown")evidence.page_errors++;
    else if(message.method==="Network.requestWillBeSent" && /^https?:/.test(message.params.request.url))evidence.external_requests++;
  });
  await rpc("Runtime.enable");await rpc("Page.enable");await rpc("Network.enable");
  await rpc("Emulation.setDeviceMetricsOverride",{width:1280,height:920,deviceScaleFactor:1,mobile:false});
  await rpc("Page.navigate",{url:pathToFileURL(path.resolve(htmlFile)).href});
  await waitPage();
  check(await evaluate("document.documentElement.lang==='en' && document.documentElement.dir==='ltr'"),"English-LTR");
  check(await evaluate("JSON.parse(document.getElementById('trace-data').textContent).every(d=>d.nodes.every(n=>!('content' in n)))"),"no-raw-content-field");
  check(await evaluate("document.querySelector('#back').disabled"),"root-back-disabled");
  const uploadScenario = await evaluate("JSON.parse(document.getElementById('trace-data').textContent).some(d=>d.id==='conflicting-uploads')");
  if(uploadScenario){
    check(await evaluate("document.querySelector('#scenario').selectedOptions[0].textContent==='Photo uploads · conflicting reports'"),"conflicting-uploads-open-first");
    await clickNode("f0","Finding");
    check(await evaluate("document.querySelectorAll('#references button[data-node^=i]').length===3"),"three-upload-observations");
    for(const [id,statement] of [["i0","Uploading a 12 MB photo failed."],["i1","Uploading another 12 MB photo succeeded."],["i2","Uploading a 2 MB photo succeeded."]]){
      await clickNode(id,"Observation");
      check(await evaluate("document.querySelector('#detail-description').textContent==="+JSON.stringify(statement)),"upload-statement-"+id);
      await evaluate("document.getElementById('back').click()");
    }
    await evaluate("document.getElementById('root').click()");
  }
  await screenshot("desktop.png");
  await clickNode("f0","Finding");await clickNode("i0","Observation");
  await clickNode("e0","Evidence");await clickNode("s0","Source");
  check(await evaluate("document.getElementById('back').click();document.getElementById('detail-kind').textContent==='Evidence'"),"back-navigation");
  check(await evaluate("document.querySelector('#breadcrumbs button').click();document.getElementById('detail-kind').textContent==='Insight'"),"breadcrumb-root");
  await evaluate("document.getElementById('scenario').value='1';document.getElementById('scenario').dispatchEvent(new Event('change'))");
  check(await evaluate("Array.from(document.querySelectorAll('.metric b')).map(n=>n.textContent).join(',')==='5,5,5,2,1'"),"five-evidence-counts");
  await clickNode("f3","Finding");
  check(await evaluate("Array.from(document.querySelectorAll('#references button[data-node^=\"i\"]')).map(n=>n.dataset.node).join(',')==='i3,i4'"),"exact-group-references");
  await evaluate("document.getElementById('search').value='Evidence';document.getElementById('search').dispatchEvent(new Event('input'))");
  check(await evaluate("document.querySelectorAll('#node-list button').length===5"),"evidence-search");
  await evaluate("document.getElementById('search').value='zz-no-match';document.getElementById('search').dispatchEvent(new Event('input'))");
  check(await evaluate("document.querySelectorAll('#node-list button').length===0 && document.getElementById('node-list').textContent.includes('No matches found')"),"empty-search-state");
  await evaluate("document.getElementById('scenario').value='2';document.getElementById('scenario').dispatchEvent(new Event('change'))");
  await clickNode("f24","Finding");await clickNode("i24","Observation");
  await clickNode("e24","Evidence");await clickNode("s24","Source");
  check(await evaluate("document.getElementById('root').click();document.getElementById('detail-kind').textContent==='Insight'"),"root-navigation");
  await rpc("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:false});
  check(await evaluate("document.documentElement.scrollWidth<=innerWidth+1"),"mobile-no-horizontal-overflow");
  await screenshot("mobile.png");
  await evaluate("document.getElementById('search').focus()");
  check(await evaluate("document.activeElement.id==='search'"),"search-focus");
  check(evidence.page_errors===0,"no-page-errors");
  check(evidence.external_requests===0,"no-external-page-requests");
  evidence.status="PASS";
}catch(error){
  evidence.status="FAIL";evidence.failed_check=error.message;
}finally{
  fs.writeFileSync(path.join(outputDirectory,"browser-results.json"),JSON.stringify(evidence,null,2));
  if(socket?.readyState===1){try{await rpc("Browser.close");}catch{}socket.close();}
  for(const item of pending.values()){clearTimeout(item.timer);item.reject(new Error("browser closed"));}
  if(browser.exitCode===null && process.platform==="win32")spawnSync("taskkill",["/PID",String(browser.pid),"/T","/F"],{stdio:"ignore"});
  else if(browser.exitCode===null)browser.kill();
  try{fs.rmSync(profile,{recursive:true,force:true,maxRetries:10,retryDelay:100});}catch{}
}
console.log(JSON.stringify(evidence));
process.exitCode=evidence.status==="PASS"?0:1;
