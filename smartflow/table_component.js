export default function(component) {
  const {data, parentElement, setStateValue} = component;
  const root = parentElement.querySelector('.sf-grid');
  root.replaceChildren();
  Object.entries(data.colors).forEach(([key, value]) => root.style.setProperty('--'+key, value));
  let rows = data.rows.map(row => row.slice());
  let sortColumn = -1, ascending = true;
  const node = (tag, text, parent) => {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (parent) parent.appendChild(element);
    return element;
  };
  const toolbar = node('div', undefined, root); toolbar.className='toolbar';
  const caption = node('span', data.editable ? 'Editable team details' : 'Results table', toolbar);
  const filter = node('input', undefined, toolbar);
  filter.type='search'; filter.placeholder='Filter rows'; filter.setAttribute('aria-label','Filter table rows');
  const download = node('button','Export CSV',toolbar); download.type='button';
  const csv = value => '"'+String(value ?? '').replaceAll('"','""')+'"';
  download.onclick = () => {
    const contents = [data.columns, ...rows].map(row => row.map(csv).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([contents],{type:'text/csv;charset=utf-8'}));
    const a=node('a'); a.href=url; a.download='smartflow_table.csv'; a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const scroller=node('div',undefined,root); scroller.className='table-scroll';
  scroller.tabIndex=0; scroller.setAttribute('role','region'); scroller.setAttribute('aria-label',data.editable?'Editable team table':'Scrollable results table');
  const table=node('table',undefined,scroller);
  const tableCaption=node('caption',data.editable?'Team member names, registration numbers and contributions':'Measured results',table);
  tableCaption.className='sr-only';
  const head=node('thead',undefined,table), heading=node('tr',undefined,head);
  const body=node('tbody',undefined,table);
  const publish=()=>setStateValue('rows', rows.map(row=>row.slice()));
  const renderRows = () => {
    body.replaceChildren();
    let visible=rows.map((row,index)=>({row,index})).filter(item=>item.row.some(value=>String(value??'').toLowerCase().includes(filter.value.toLowerCase())));
    if(sortColumn>=0) visible.sort((a,b)=>{
      const x=a.row[sortColumn],y=b.row[sortColumn];
      const result=typeof x==='number'&&typeof y==='number'?x-y:String(x??'').localeCompare(String(y??''),undefined,{numeric:true});
      return ascending?result:-result;
    });
    for(const {row,index} of visible){
      const tr=node('tr',undefined,body);
      row.forEach((value,column)=>{
        const td=node('td',undefined,tr);
        if(data.editable){
          const input=node('input',undefined,td); input.type='text'; input.value=value??'';
          input.setAttribute('aria-label',data.columns[column]+' row '+(index+1));
          input.onchange=()=>{rows[index][column]=input.value;publish();};
        } else td.textContent=typeof value==='number'?new Intl.NumberFormat(undefined,{maximumFractionDigits:4}).format(value):String(value??'');
      });
      if(data.editable){
        const td=node('td',undefined,tr), remove=node('button','Remove',td);remove.type='button';
        remove.setAttribute('aria-label','Remove team member row '+(index+1));
        remove.onclick=()=>{rows.splice(index,1);publish();renderRows();};
      }
    }
    caption.textContent=(data.editable?'Editable team details':'Results table')+' · '+visible.length+' / '+rows.length+' rows';
  };
  data.columns.forEach((label,column)=>{
    const th=node('th',undefined,heading);th.scope='col';
    const button=node('button',label,th);button.type='button';button.title='Sort by '+label;
    button.onclick=()=>{
      ascending=sortColumn===column?!ascending:true;sortColumn=column;
      heading.querySelectorAll('th').forEach(el=>el.removeAttribute('aria-sort'));
      th.setAttribute('aria-sort',ascending?'ascending':'descending');renderRows();
    };
  });
  if(data.editable)node('th','Actions',heading);
  filter.oninput=renderRows;
  if(data.editable){
    const add=node('button','Add team member',root);add.type='button';add.className='add-row';
    add.onclick=()=>{rows.push(data.columns.map(()=>''));filter.value='';publish();renderRows();};
  }
  renderRows();
}
