/* ---------- revenue tab ---------- */
const REV=__REV_DATA__;
const rvState={h:2,area:'SE3',prod:'n'};
const MIXES=REV.scenarios.map(s=>s.mix_id).filter((v,i,a)=>a.indexOf(v)===i);
const grp=x=>String(x).replace(/\B(?=(\d{3})+(?!\d))/g,'\u202f');
const eur=v=>(v<0?'−€':'€')+grp(Math.round(Math.abs(v)));
const eurK=v=>(v<0?'−€':'€')+(Math.abs(v)/1000).toFixed(Math.abs(v)<10000?1:0)+'k';
const rvA=()=>({spot:{SE1:num('rv-spot1',-500,2000,50),SE2:num('rv-spot2',-500,2000,50),SE3:num('rv-spot3',-500,2000,50)},
  wear:num('rv-wear',0,500,10),aux:num('rv-aux',0,50,2.5),fee:num('rv-fee',0,100,10)/100,avail:num('rv-avail',0,100,100)/100});
function rvNet(s,a,area,wearOverride){
  const spot=a.spot[area],gross=s.gross_EUR*a.avail,hours=s.hours;
  const energy=spot*(s.import_MWh-s.export_MWh-s.soc_change_MWh);
  const aux=a.aux*s.energy_MWh/1000*hours*spot;
  const wear=(wearOverride==null?a.wear:wearOverride)*s.throughput_MWh;
  const fee=a.fee*gross;
  return {mix:s.mix,mix_id:s.mix_id,cn:s.c_fcrn_MW,cdu:s.c_fcrd_up_MW,cdd:s.c_fcrd_down_MW,gross,energy,aux,wear,fee,net:gross-energy-aux-wear-fee,thr:s.throughput_MWh};
}
function rvRows(){const a=rvA();return REV.scenarios.filter(s=>s.storage_h===rvState.h).map(s=>rvNet(s,a,rvState.area)).sort((x,y)=>y.net-x.net)}
function rvSeg(sel,attr,val){document.querySelectorAll(sel).forEach(b=>b.setAttribute('aria-pressed',String(b.dataset[attr]===String(val))))}
function drawRev(){
  if($('tab-rev').hidden)return;
  rvSeg('.rv-st','h',rvState.h);rvSeg('.rv-ar','a',rvState.area);rvSeg('.rv-pp','p',rvState.prod);
  const a=rvA(),rows=rvRows(),best=rows[0];
  const get=id=>rows.find(r=>r.mix_id===id);
  const N=get('n_only'),D=get('d_both');
  $('rv-best-net').textContent=eur(best.net);$('rv-best-name').textContent='Best: '+best.mix+', net';
  $('rv-n-net').textContent=eur(N.net);$('rv-d-net').textContent=eur(D.net);
  $('rv-year').textContent=eurK(best.net*12);
  const n0=rvNet(REV.scenarios.find(s=>s.storage_h===rvState.h&&s.mix_id==='n_only'),a,rvState.area,0).net,d0=rvNet(REV.scenarios.find(s=>s.storage_h===rvState.h&&s.mix_id==='d_both'),a,rvState.area,0).net;
  const be=(n0-d0)/(N.thr-D.thr);
  $('rv-be').textContent=be>0?'€'+be.toFixed(0)+'/MWh':'always';
  const du=[...REV.prices.du].sort((x,y)=>y-x),dsum=REV.prices.du.reduce((s,x)=>s+x,0);
  $('rv-spike').textContent=Math.round(du.slice(0,6).reduce((s,x)=>s+x,0)/dsum*100)+' %';
  // bars
  const bars=$('rv-bars');bars.replaceChildren();
  const maxG=Math.max(...rows.map(r=>r.gross),1);
  rows.forEach(r=>{const row=document.createElement('div');row.className='rv-bar';
    const l=document.createElement('span');l.className='rv-bl';l.textContent=r.mix;
    const t=document.createElement('div');t.className='rv-track';
    const g=document.createElement('div');g.className='rv-g';g.style.width=(r.gross/maxG*100)+'%';
    const nb=document.createElement('div');nb.className='rv-n'+(r.net<0?' neg':'');nb.style.width=(Math.abs(r.net)/maxG*100)+'%';
    const v=document.createElement('span');v.className='rv-bv';
    const b=document.createElement('b');b.textContent=eur(r.net);v.append(b,document.createTextNode(' of '+eur(r.gross)));
    t.append(g,nb);row.append(l,t,v);bars.appendChild(row)});
  // table
  const tb=document.querySelector('#rv-table tbody');tb.replaceChildren();
  rows.forEach((r,i)=>{const tr=document.createElement('tr');if(i===0)tr.className='rv-best';
    [[r.mix],[r.cn.toFixed(2)],[r.cdu.toFixed(2)],[r.cdd.toFixed(2)],[eur(r.gross)],[eur(r.energy),'c'],[eur(r.aux),'c'],[eur(r.wear),'c'],[eur(r.fee),'c'],[eur(r.net),'n'],[r.thr.toFixed(1)+' MWh']]
    .forEach(([t,c],j)=>{const td=document.createElement(j?'td':'th');if(!j)td.scope='row';td.textContent=t;if(c==='c')td.className='rv-cost';if(c==='n')td.className='rv-net';tr.appendChild(td)});tb.appendChild(tr)});
  drawWear(a);drawPrice();drawDay(a);drawAreas();
}
function drawWear(a){
  const box=$('rv-wear-chart');box.replaceChildren();
  const ids=[['n_only','--fcrn'],['n50_d50','--nem'],['d_both','--fcrd'],['d_up','--trace']];
  const W=Math.max(280,box.clientWidth),H=240,L0=8,B=26,T=10,R=10;
  const ser=ids.map(([id,col])=>{const s=REV.scenarios.find(x=>x.storage_h===rvState.h&&x.mix_id===id);
    return {name:s.mix,col,pts:[0,5,10,15,20,25,30,35,40].map(w=>({w,v:rvNet(s,a,rvState.area,w).net}))}});
  $('rv-wear-legend').replaceChildren(...ser.map(s=>{const sp=document.createElement('span');const i=document.createElement('i');i.className='ln';i.style.setProperty('--c','var('+s.col+')');sp.append(i,document.createTextNode(s.name));return sp}));
  const all=ser.flatMap(s=>s.pts.map(p=>p.v));let lo=Math.min(0,...all),hi=Math.max(...all);
  const raw=Math.max(1,(hi-lo)/5),mag=Math.pow(10,Math.floor(Math.log10(raw))),q=raw/mag;
  const step=mag*(q<1.5?1:q<3?2:q<7?5:10);
  const kf=v=>(v<0?'−€':'€')+(Math.abs(v)%1000===0?Math.abs(v)/1000:(Math.abs(v)/1000).toFixed(1))+'k';
  lo=Math.floor(lo/step)*step;hi=Math.ceil(hi/step)*step;
  const ticks=[];for(let v=lo;v<=hi+1e-9;v+=step)ticks.push(v);
  const NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.setAttribute('width','100%');svg.setAttribute('role','img');svg.setAttribute('aria-label','Net revenue against battery wear cost');
  const mk=(tag,at)=>{const e=document.createElementNS(NS,tag);for(const k in at)e.setAttribute(k,at[k]);svg.appendChild(e);return e};
  box.appendChild(svg);
  let L=L0;ticks.forEach(v=>{const t=mk('text',{'font-size':11,x:0,y:0});t.textContent=kf(v);L=Math.max(L,t.getComputedTextLength()+10);t.remove()});
  const x=w=>L+(W-L-R)*w/40,y=v=>T+(H-T-B)*(1-(v-lo)/(hi-lo||1));
  ticks.forEach(v=>{mk('line',{x1:L,x2:W-R,y1:y(v),y2:y(v),stroke:css('--line'),'stroke-width':1});const t=mk('text',{x:L-6,y:y(v),dy:'0.32em','text-anchor':'end','font-size':11,fill:css('--muted')});t.textContent=kf(v)});
  [0,10,20,30,40].forEach(w=>{const t=mk('text',{x:x(w),y:H-6,'text-anchor':w===0?'start':w===40?'end':'middle','font-size':11,fill:css('--muted')});t.textContent='€'+w+'/MWh'});
  ser.forEach(s=>{mk('polyline',{points:s.pts.map(p=>x(p.w)+','+y(p.v)).join(' '),fill:'none',stroke:css(s.col),'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'});
    s.pts.forEach(p=>{const c=mk('circle',{cx:x(p.w),cy:y(p.v),r:3,fill:css(s.col)});const tt=document.createElementNS(NS,'title');tt.textContent=s.name+': '+eur(p.v)+' at €'+p.w+'/MWh wear';c.appendChild(tt)})});
  const cw=a.wear;if(cw>=0&&cw<=40){mk('line',{x1:x(cw),x2:x(cw),y1:T,y2:H-B,stroke:css('--band'),'stroke-dasharray':'4 4'});const t=mk('text',{x:Math.min(x(cw)+4,W-R-60),y:T+10,'font-size':10,fill:css('--muted')});t.textContent='your €'+cw}
}
let rvPlot=null;
function drawPrice(){
  const box=$('rv-price');if(rvPlot){rvPlot.destroy();rvPlot=null}box.replaceChildren();
  const key=rvState.prod,col={n:'--fcrn',du:'--fcrd',dd:'--chg'}[key];
  const ys=REV.prices[key],xs=ys.map((_,i)=>i);
  const t0=new Date(REV.prices.t0.replace(' ','T')+'Z');
  const lab=i=>{const d=new Date(t0.getTime()+i*3600e3);return d.toLocaleDateString('en-GB',{day:'numeric',month:'short',timeZone:'UTC'})};
  const labT=i=>{const d=new Date(t0.getTime()+i*3600e3);return lab(i)+' '+String(d.getUTCHours()).padStart(2,'0')+':00'};
  const g={stroke:css('--muted'),grid:{stroke:css('--line'),width:1},ticks:{stroke:css('--line'),width:1}};
  const W=Math.max(280,box.clientWidth);
  rvPlot=new uPlot({width:W,height:Math.max(200,Math.min(300,Math.round(W*0.3))),scales:{x:{time:false}},legend:{show:false},
    cursor:{points:{show:false},drag:{x:true,y:false}},
    axes:[{...g,values:(u,vs)=>vs.map(v=>lab(v)),space:70,incrs:[24,48,72,96,168,336]},{...g,size:52,values:(u,vs)=>vs.map(v=>'€'+v)}],
    series:[{},{stroke:css(col),width:1.5,points:{show:false}}],
    hooks:{setCursor:[u=>{const i=u.cursor.idx;$('rv-price-ro').textContent=i==null?'':labT(i)+'  €'+ys[i].toFixed(2)+'/MW'}]}},[xs,ys],box);
  const ps=$('rv-psum');ps.replaceChildren();
  [['n','FCR-N'],['du','FCR-D up'],['dd','FCR-D down']].forEach(([k,name])=>{const arr=REV.prices[k],s=arr.reduce((a,b)=>a+b,0),m=[...arr].sort((a,b)=>a-b)[Math.floor(arr.length/2)];
    const d=document.createElement('div');d.className='stat';const b=document.createElement('b');b.className=k==='n'?'fn':'fd';b.textContent=eur(s);const sp=document.createElement('span');sp.textContent=name+' per MW for the period (median €'+m.toFixed(1)+'/MW·h)';d.append(b,sp);ps.appendChild(d)});
}
function drawDay(a){
  $('rv-day-name').textContent=longDate(curDay);
  const t0=new Date(REV.prices.t0.replace(' ','T')+'Z'),d=new Date(curDay+'T00:00:00Z');
  const i0=Math.round((d-t0)/3600e3),len=REV.prices.n.length;
  const ids=['rv-dg','rv-de','rv-dw','rv-dn'];
  if(i0<0||i0+24>len){ids.forEach(id=>$(id).textContent='–');$('rv-day-note').textContent='No FCR prices for this day. Prices cover '+REV.period[0]+' to '+REV.period[1]+'. Pick a day in that range on the Simulator tab, or load its Fingrid file.';return}
  const {CN,CDu,CDd}=caps(),CAP=num('in-e',0.1,400,2),S0=num('in-s0',0,100,50),spot=a.spot[rvState.area];
  let gross=0;for(let h=i0;h<i0+24;h++)gross+=CN*REV.prices.n[h]+CDu*REV.prices.du[h]+CDd*REV.prices.dd[h];gross*=a.avail;
  let imp=0,exp=0;for(let i=0;i<n;i++){const v=p[i];if(v>0)exp+=v;else imp-=v}imp*=DT;exp*=DT;
  const dsoc=(soc[n-1]-S0)/100*CAP;
  const energy=spot*(imp-exp-dsoc),aux=a.aux*CAP/1000*24*spot,wear=a.wear*(imp+exp),fee=a.fee*gross;
  $('rv-dg').textContent=eur(gross);$('rv-de').textContent=eur(energy+aux);$('rv-dw').textContent=eur(wear+fee);$('rv-dn').textContent=eur(gross-energy-aux-wear-fee);
  $('rv-day-note').textContent='Uses the battery ('+num('in-p',0.1,100,1)+' MW / '+CAP+' MWh), capacities (FCR-N '+CN.toFixed(2)+', FCR-D up '+CDu.toFixed(2)+', FCR-D down '+CDd.toFixed(2)+' MW), start SOC and energy management from the Simulator tab, with the costs above at the '+rvState.area+' spot price. One day starting at '+S0+' % SOC, so energy cost includes refilling the battery to where it started.';
}
function drawAreas(){
  const tb=document.querySelector('#rv-areas tbody');tb.replaceChildren();
  ['SE1','SE2','SE3'].forEach(ar=>{const v=REV.volumes[ar],tr=document.createElement('tr');
    [ar,v.n.toFixed(1),v.du.toFixed(1),v.dd.toFixed(1)].forEach((t,j)=>{const td=document.createElement(j?'td':'th');if(!j)td.scope='row';td.textContent=t;tr.appendChild(td)});tb.appendChild(tr)});
}
document.querySelectorAll('.rv-st').forEach(b=>b.addEventListener('click',()=>{rvState.h=+b.dataset.h;drawRev()}));
document.querySelectorAll('.rv-ar').forEach(b=>b.addEventListener('click',()=>{rvState.area=b.dataset.a;drawRev()}));
document.querySelectorAll('.rv-pp').forEach(b=>b.addEventListener('click',()=>{rvState.prod=b.dataset.p;rvSeg('.rv-pp','p',rvState.prod);drawPrice()}));
let rvT;['rv-spot1','rv-spot2','rv-spot3','rv-wear','rv-aux','rv-fee','rv-avail'].forEach(id=>$(id).addEventListener('input',()=>{clearTimeout(rvT);rvT=setTimeout(drawRev,250)}));
$('rv-reset').addEventListener('click',()=>{[['rv-spot1',50],['rv-spot2',50],['rv-spot3',50],['rv-wear',10],['rv-aux',2.5],['rv-fee',10],['rv-avail',100]].forEach(([id,v])=>$(id).value=v);drawRev()});
$('rv-period').textContent=longDate(REV.period[0])+' – '+longDate(REV.period[1]);
/* ---------- tabs ---------- */
function showTab(t){const rev=t==='revenue';$('tab-sim').hidden=rev;$('tab-rev').hidden=!rev;
  $('tb-sim').setAttribute('aria-selected',String(!rev));$('tb-rev').setAttribute('aria-selected',String(rev));
  $('tb-sim').tabIndex=rev?-1:0;$('tb-rev').tabIndex=rev?0:-1;
  try{history.replaceState(null,'',rev?'#revenue':'#simulator')}catch(e){}
  if(rev)drawRev();else build()}
$('tb-sim').addEventListener('click',()=>showTab('simulator'));
$('tb-rev').addEventListener('click',()=>showTab('revenue'));
document.querySelector('.tabs').addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key==='ArrowLeft'){const rev=$('tab-rev').hidden;showTab(rev?'revenue':'simulator');(rev?$('tb-rev'):$('tb-sim')).focus()}});
window.addEventListener('resize',()=>{clearTimeout(rvT);rvT=setTimeout(drawRev,200)});
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',drawRev);
new MutationObserver(drawRev).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
