(() => {
  'use strict';
  const d = JSON.parse(document.querySelector('#report-data').textContent);
  const $ = (id) => document.getElementById(id);
  const fmt = (v, dp = 1) => v == null ? '—' : Number(v).toLocaleString('en-US', {maximumFractionDigits: dp});
  const el = (tag, text, cls) => {const x = document.createElement(tag); if(text != null) x.textContent = String(text); if(cls) x.className=cls; return x;};
  const metricLabels = [
    ['p95_us','P95 DISPATCH','95th percentile','◈','positive'],
    ['max_us','WORST DISPATCH','Observed maximum','⌁','warn'],
    ['samples','DISPATCH SAMPLES','Completed ready → running','⌘',''],
    ['breaches','OVER THRESHOLD','Configured screening threshold','⚑','warn'],
  ];
  for(const [key,label,subtitle,icon,variant] of metricLabels){
    const card = el('article',null,`metric ${variant}`);
    card.append(el('div',label,'metric-label'),el('div',icon,'metric-icon'));
    const number = el('div',fmt(d.metrics[key], key === 'samples' || key === 'breaches' ? 0 : 2),'metric-value');
    if(key.endsWith('_us')) number.append(el('small','µs'));
    card.append(number,el('div',subtitle,'metric-note'));$('metrics').append(card);
  }
  $('snapshot').textContent = `${fmt(d.trace.duration_us / 1000)} MS CAPTURE  ·  ${d.trace.cpu_count} CPUs`;
  $('sample-count').textContent = `${fmt(d.metrics.samples,0)} samples`;
  $('synthetic-alert').hidden = d.trace.system_release !== '8.0-synthetic';
  $('budget').value = d.budget_us;
  const dispatches = d.dispatches || [];
  function budgetChange(){
    const budget = Number($('budget').value);
    if(!(budget>0) || !Number.isFinite(budget)) return;
    const breaches = dispatches.filter(x=>x.latency_us>budget).length;
    const within = dispatches.length-breaches;
    const pct = dispatches.length?100*within/dispatches.length:0;
    $('gauge-pct').textContent = `${fmt(pct)}%`;
    $('gauge-bar').style.width = `${pct}%`;
    $('within-count').textContent = `${fmt(within,0)} within`;
    $('breach-count').textContent = `${fmt(breaches,0)} exceeded`;
    renderThreads(budget);
  }
  $('budget').addEventListener('input', budgetChange);
  $('thread-filter').addEventListener('input', budgetChange);
  function td(row, value, className=''){const cell=el('td',value,className);row.append(cell);return cell;}
  function renderThreads(budget){
    const query = $('thread-filter').value.trim();
    const tbody=$('thread-rows');tbody.replaceChildren();
    const rows=d.threads.filter(x=>!query || `${x.pid}:${x.tid}`.includes(query));
    const max=Math.max(1,...rows.map(x=>x.max_us));
    for(const x of rows){
      const count = dispatches.filter(z=>z.pid===x.pid && z.tid===x.tid && z.latency_us>budget).length;
      const row=el('tr');td(row,`${x.pid}:${x.tid}`,'thread-code');td(row,x.samples);
      td(row,`${fmt(x.p95_us)} µs`);td(row,`${fmt(x.max_us)} µs`,x.max_us>budget?'danger':'good');
      td(row,count,count?'danger':'good');
      const cell=td(row,'');const pressure=el('div',null,'pressure');const fill=el('span',null,x.max_us>budget?'high':'');
      fill.style.width=`${100*x.max_us/max}%`;pressure.append(fill);cell.append(pressure);tbody.append(row);
    }
    if(!rows.length){const row=el('tr');const cell=td(row,'No matching threads');cell.colSpan=6;tbody.append(row);}
  }
  function makeDistribution(){
    const target=$('distribution');if(!dispatches.length){target.textContent='No dispatch observations available';return;}
    const values=dispatches.map(x=>x.latency_us);const upper=Math.max(1,...values);
    const bins=14;const counts=Array(bins).fill(0);
    for(const x of values) counts[Math.min(bins-1,Math.floor(x/upper*bins))]++;
    const max=Math.max(...counts,1);const width=680,height=210,pad=28,gap=7;
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    for(let i=0;i<4;i++){
      const y=15+i*48;const line=document.createElementNS(svg.namespaceURI,'line');
      for(const [k,v] of Object.entries({x1:pad,y1:y,x2:width-6,y2:y,class:'axis-line'}))line.setAttribute(k,v);svg.append(line);
      const text=document.createElementNS(svg.namespaceURI,'text');text.setAttribute('x','4');text.setAttribute('y',String(y+3));text.setAttribute('class','axis-text');text.textContent=String(Math.ceil(max*(3-i)/3));svg.append(text);
    }
    const barWidth=(width-pad-20)/bins-gap;
    counts.forEach((count,i)=>{
      const h=Math.max(count?3:0,158*count/max),x=pad+5+i*(barWidth+gap),y=173-h;
      const rect=document.createElementNS(svg.namespaceURI,'rect');
      for(const [k,v] of Object.entries({x,y,width:barWidth,height:h,rx:2,class:'bar'}))rect.setAttribute(k,String(v));
      const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=`${fmt(i*upper/bins)}–${fmt((i+1)*upper/bins)} µs: ${count} dispatches`;rect.append(title);svg.append(rect);
    });
    for(let i=0;i<=4;i++){
      const tick=document.createElementNS(svg.namespaceURI,'text');tick.setAttribute('x',String(pad+5+i*(width-pad-20)/4));
      tick.setAttribute('y','198');tick.setAttribute('class','axis-text');tick.textContent=`${fmt(i*upper/4)} µs`;svg.append(tick);
    }
    target.append(svg);
  }
  function renderTimeline(){
    const parent=$('timeline-body');const total=d.trace.duration_us || 1;
    const colors=['#46bcac','#6b91c6','#c99d62','#9073c7','#c57785','#4baca0','#9ca868'];
    for(let cpu=0;cpu<d.trace.cpu_count;cpu++){
      const row=el('div',null,'timeline-row');row.append(el('div',`CPU ${cpu}`,'timeline-label'));
      const track=el('div',null,'timeline-track');
      for(const s of d.segments.filter(x=>x.cpu===cpu)){
        const span=el('div',null,'timeline-span');span.style.left=`${Math.min(100,100*s.start_us/total)}%`;
        span.style.width=`${Math.max(.08,100*(s.end_us-s.start_us)/total)}%`;
        span.style.background=colors[Math.abs(s.pid*7+s.tid)%colors.length];
        span.title=`PID ${s.pid} / TID ${s.tid} · ${fmt(s.end_us-s.start_us)} µs observed`;track.append(span);
      }
      row.append(track);parent.append(row);
    }
  }
  function renderEvents(){
    for(const x of d.worst_dispatches){
      const row=el('tr');td(row,`${x.pid}:${x.tid}`,'thread-code');td(row,`CPU ${x.cpu}`);
      td(row,`${fmt(x.start_us)} µs`);td(row,`${fmt(x.run_us)} µs`);
      td(row,`${fmt(x.latency_us)} µs`,x.over_budget?'danger':'good');
      td(row,`${x.ready_line} → ${x.run_line}`);$('event-rows').append(row);
    }
  }
  function renderWarnings(){
    const parent=$('warnings');
    for(const warning of d.warnings)parent.append(el('div',`⚠  ${warning}`,'warning'));
    if(!d.warnings.length)parent.append(el('div','✓  No parser or sampling warnings reported.','warning ok'));
    const fields=[['TARGET RELEASE',d.trace.system_release],['CLOCK',`${fmt(d.trace.cycles_per_second,0)} Hz`],['TRACE EVENTS',fmt(d.trace.event_count,0)]];
    for(const [key,value] of fields){const item=el('div');item.append(el('div',key,'prov-label'),el('div',value,'prov-value'));$('provenance').append(item);}
  }
  $('download-json').addEventListener('click',()=>{
    const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='pulseguard-report.json';a.click();
    setTimeout(()=>URL.revokeObjectURL(url),2000);
  });
  const links=[...document.querySelectorAll('.nav-item')];
  links.forEach(link=>link.addEventListener('click',()=>{links.forEach(x=>x.classList.remove('active'));link.classList.add('active');}));
  makeDistribution();renderTimeline();renderEvents();renderWarnings();budgetChange();
})();
