// DOM behavior checks, not browser rendering or screenshot tests.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../smartflow/table_component.js',import.meta.url),'utf8');
const render=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).default;
class Element {
  constructor(tag){this.tagName=tag;this.children=[];this.attributes={};this.style={values:{},setProperty(k,v){this.values[k]=v;}};this.value='';this.textContent='';}
  appendChild(child){this.children.push(child);return child;}
  replaceChildren(...children){this.children=children;}
  setAttribute(key,value){this.attributes[key]=value;}
  removeAttribute(key){delete this.attributes[key];}
  querySelectorAll(tag){return this.children.flatMap(c=>[...(c.tagName===tag?[c]:[]),...c.querySelectorAll(tag)]);}
  click(){if(this.onclick)this.onclick();}
}
globalThis.document={createElement:tag=>new Element(tag)};
for(const [background,text] of [['#FFFFFF','#0F172A'],['#172238','#F8FAFC']]){
  const root=new Element('div'), state={};
  const data={editable:true,columns:['Name','Registration','Contribution'],rows:[['Original','R1','']],colors:{card:background,text,surface:background,border:'#CBD5E1',accent:'#0284C7',selected:background}};
  const mount=()=>render({data,parentElement:{querySelector:()=>root},setStateValue:(key,value)=>{state[key]=structuredClone(value);}});
  mount();
  assert.equal(root.style.values['--card'],background);
  const inputs=()=>root.querySelectorAll('input');
  inputs()[1].value='Edited';inputs()[1].onchange();
  assert.equal(state.rows[0][0],'Edited');
  root.querySelectorAll('button').find(b=>b.textContent==='Add team member').click();
  assert.equal(state.rows.length,2);
  root.querySelectorAll('button').find(b=>b.attributes['aria-label']==='Remove team member row 1').click();
  assert.equal(state.rows.length,1);
  data.rows=state.rows;mount();
  assert.equal(inputs()[1].value,''); // Only the added blank row remains.
  data.editable=false;data.columns=['Queue'];data.rows=[[10],[2],[-3]];mount();
  root.querySelectorAll('th')[0].querySelectorAll('button')[0].click();
  assert.equal(root.querySelectorAll('tbody')[0].querySelectorAll('td')[0].textContent,'-3');
  inputs()[0].value='10';inputs()[0].oninput();
  assert.equal(root.querySelectorAll('tbody')[0].querySelectorAll('tr').length,1);
  assert.equal(root.querySelectorAll('tbody')[0].querySelectorAll('td')[0].textContent,'10');
  let downloaded;
  URL.createObjectURL=blob=>{downloaded=blob;return 'blob:test';};URL.revokeObjectURL=()=>{};
  root.querySelectorAll('button').find(b=>b.textContent==='Export CSV').click();
  assert.equal(await downloaded.text(),'"Queue"\r\n"10"\r\n"2"\r\n"-3"');
}
console.log('PASS: both palettes, editable cells, add/remove, numeric sort, negative values, filtering, row labels and lossless CSV export.');
