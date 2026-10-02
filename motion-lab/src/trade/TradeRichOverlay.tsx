import React, {type CSSProperties,useEffect,useRef,useState} from 'react';
import {AbsoluteFill, Easing, cancelRender,continueRender,delayRender,interpolate, useCurrentFrame} from 'remotion';
import {jedTokens as t} from '../visual-a/tokens';

export const richPalette = {blue:'#2D6BFF',teal:'#087D88',gold:'#A76D0B',violet:'#7250BE',ink:'#081224',muted:'#34445A'};
export type RichKind = 'excel-pain'|'pricing-flow'|'ai-route'|'pricing-modes'|'refund-compare'|'export-file'|'history-reuse'|'audience'|'source-cta';
export type RichNode = {label:string;detail?:string;color?:string;cue:number;icon?:'sheet'|'coin'|'chat'|'cloud'|'person'|'code'|'copy'|'check'};
export type TradeRichProps = {durationInFrames:number;kind:RichKind;eyebrow:string;heading:string;nodes:RichNode[];conclusion?:string;conclusionCue?:number};
const ease={easing:Easing.out(Easing.cubic),extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
const color=(name:string|undefined,i:number)=>richPalette[name as keyof typeof richPalette]??name??[richPalette.blue,richPalette.teal,richPalette.gold,richPalette.violet][i%4];

/** Each icon is an actual small drawing. Text has no stroke, glow or shadow. */
const Icon:React.FC<{kind:RichNode['icon'];color:string;size?:number}>=({kind,color:ink,size=40})=><svg width={size} height={size} viewBox="0 0 40 40" fill="none" stroke={ink} strokeWidth="2.1" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
  {kind==='coin'?<><circle cx="20" cy="20" r="15"/><path d="M13 11l7 9 7-9M14 22h12M14 27h12M20 20v12"/></>:kind==='chat'?<><path d="M6 6h28v21H18l-9 7v-7H6Z"/><path d="M12 13h16M12 19h10"/></>:kind==='cloud'?<><path d="M10 29a8 8 0 01-1-16 11 11 0 0121-1 8 8 0 011 17Z"/><path d="M15 21l5-5 5 5M20 16v17"/></>:kind==='person'?<><circle cx="20" cy="12" r="7"/><path d="M7 34v-5c0-6 26-6 26 0v5M7 34h26"/></>:kind==='code'?<><path d="M12 12L4 20l8 8M28 12l8 8-8 8M23 7l-6 26"/></>:kind==='copy'?<><path d="M13 5h21v24H13Z"/><path d="M8 11H5v24h21v-3M18 12h11M18 18h11M18 24h8"/></>:kind==='check'?<><circle cx="20" cy="20" r="15"/><path d="M11 20l6 6 13-13"/></>:<><path d="M9 4h17l6 6v26H9Z"/><path d="M26 4v7h6M14 17h13M14 23h13M14 29h9"/></>}
</svg>;

/** Measure actual loaded font glyphs. Preserve all words rather than clipping a box. */
const FittedNode:React.FC<{n:RichNode;x:number;y:number;w:number;h:number;size:number;icon:boolean;ink:string;entry:CSSProperties;variant:'frame'|'anchor'|'rail'|'plain'|'role'}>=({n,x,y,w,h,size,icon,ink,entry,variant})=>{
 const ref=useRef<HTMLDivElement>(null);
 const [scale,setScale]=useState(1);
 const [handle]=useState(()=>delayRender('Measure rich node after font load'));
 const signature=JSON.stringify({label:n.label,detail:n.detail,w,h,size,icon,variant});
 useEffect(()=>{
  let active=true;
  document.fonts.ready.then(()=>{
   if(active&&ref.current){
    const next=Math.min(1,(h-36)/Math.max(1,ref.current.scrollHeight),(w-40)/Math.max(1,ref.current.scrollWidth));
    if(next<0.78)throw new Error(`Rich node has too much text for its frame: ${n.label}`);
    setScale(next);
   }
   continueRender(handle);
  }).catch(error=>cancelRender(error instanceof Error?error:new Error(String(error))));
  return()=>{active=false;continueRender(handle);};
 },[signature,handle,n.label,h,w]);
 return <div data-rich-node={n.label} data-content-scale={scale} style={{position:'absolute',left:x,top:y,width:w,height:h,border:variant==='frame'?`2px solid ${ink}`:'none',borderRadius:16,boxSizing:'border-box',padding:'18px 20px',...entry}}>
  {variant==='anchor'?<><div style={{position:'absolute',left:20,top:0,width:34,height:3,background:ink}}/><div style={{position:'absolute',left:0,top:18,width:3,height:27,background:ink}}/></>:null}
  {variant==='rail'?<><div style={{position:'absolute',left:0,top:0,width:25,height:25,borderTop:`2px solid ${ink}`,borderLeft:`2px solid ${ink}`}}/><div style={{position:'absolute',right:0,bottom:0,width:25,height:25,borderBottom:`2px solid ${ink}`,borderRight:`2px solid ${ink}`}}/></>:null}
  <div ref={ref} style={{width:w-40,transform:`scale(${scale})`,transformOrigin:'top left'}}>
   {icon?<div style={variant==='role'?{margin:'0 auto 15px',width:63,height:63,border:`2px solid ${ink}`,borderRadius:'50%',display:'flex',justifyContent:'center',alignItems:'center'}:h<170?{position:'absolute',left:0,top:5}:{marginBottom:11}}><Icon kind={n.icon} color={ink} size={34}/></div>:null}
   <div style={{marginLeft:icon&&h<170?54:0,textAlign:variant==='role'?'center':'left'}}><div style={{fontSize:size,fontWeight:700,lineHeight:1.2,color:ink,whiteSpace:'pre-line'}}>{n.label}</div>
    {n.detail?<div style={{fontSize:23,lineHeight:1.35,color:richPalette.muted,marginTop:9,whiteSpace:'pre-line'}}>{n.detail}</div>:null}
   </div>
  </div>
 </div>;
};

export const TradeRichOverlay:React.FC<TradeRichProps>=({durationInFrames,kind,eyebrow,heading,nodes,conclusion='',conclusionCue=0})=>{
 const frame=useCurrentFrame();
 const reveal=(cue:number,length=13)=>interpolate(frame,[cue,cue+length],[0,1],ease);
 const enter=(cue:number):CSSProperties=>({opacity:reveal(cue),transform:`translateY(${12*(1-reveal(cue))}px)`});
 const exit=interpolate(frame,[Math.max(0,durationInFrames-11),Math.max(1,durationInFrames-1)],[1,0],ease);
 const c=(i:number)=>color(nodes[i]?.color,i);
 const arrow=(x1:number,y1:number,x2:number,y2:number,cue:number,ink:string,key:string)=><g key={key} opacity={reveal(cue)}><path d={`M${x1} ${y1}L${x2} ${y2}`} fill="none" stroke={ink} strokeWidth={2.4} pathLength={1} strokeDasharray={1} strokeDashoffset={1-reveal(cue,18)}/><path d={`M${x2} ${y2}l-6 -9h12Z`} transform={`rotate(${Math.atan2(y2-y1,x2-x1)*180/Math.PI-90} ${x2} ${y2})`} fill={ink} stroke="none" opacity={reveal(cue+12,6)}/></g>;
 const node=(i:number,x:number,y:number,w:number,h:number,size=32,icon=true)=>{
  const n=nodes[i];if(!n)return null;
  const variant=kind==='pricing-flow'&&i>0&&i<4?'anchor':kind==='ai-route'?'rail':['pricing-modes','refund-compare'].includes(kind)?'plain':kind==='audience'?'role':'frame';
  return <FittedNode key={i} n={n} x={x} y={y} w={w} h={h} size={size} icon={icon} ink={c(i)} entry={enter(n.cue)} variant={variant}/>;
 };
 return <AbsoluteFill style={{backgroundColor:'transparent',fontFamily:t.font,color:richPalette.ink,pointerEvents:'none',opacity:exit,textShadow:'none',WebkitTextStroke:'0 transparent'}}>
  <div style={{position:'absolute',left:95,top:175,width:650,...enter(0)}}>
   <div style={{display:'flex',gap:12,alignItems:'center',fontSize:20,fontWeight:700,color:richPalette.blue,letterSpacing:2}}><span style={{width:28,height:3,background:richPalette.blue}}/>{eyebrow}</div>
   <div style={{fontSize:48,fontWeight:700,lineHeight:1.14,whiteSpace:'pre-line',letterSpacing:-1,marginTop:20}}>{heading}</div>
  </div>
  {kind==='excel-pain'?<>
   {node(0,95,350,298,237,32)}{node(1,425,350,320,237,32)}
   <svg style={{position:'absolute',left:95,top:625}} width={650} height={142} viewBox="0 0 650 142" aria-hidden>
    {[0,1,2].map((i)=><g key={i} opacity={reveal(nodes[2]?.cue??0)}><rect x={i*222+1} y="1" width="204" height="105" rx="8" fill="none" stroke={[richPalette.blue,richPalette.teal,richPalette.gold][i]} strokeWidth="2"/><path d={`M${i*222+1} 42h204M${i*222+65} 42v64M${i*222+132} 42v64M${i*222+1} 75h204`} stroke={[richPalette.blue,richPalette.teal,richPalette.gold][i]} strokeWidth="1.5" fill="none"/>{[0,1].map(row=><g key={row} opacity={reveal((nodes[2]?.cue??0)+i*8+row*5)}>{[0,1,2].map(col=><path key={col} d={`M${i*222+14+col*66} ${58+row*33}h32`} stroke={[richPalette.blue,richPalette.teal,richPalette.gold][i]} strokeWidth="2.2"/>)}</g>)}</g>)}
   </svg>
   <div style={{position:'absolute',left:95,top:637,width:650,display:'flex',gap:18,fontSize:23,fontWeight:700,...enter(nodes[2]?.cue??0)}}>{['成本','利润','客户报价'].map((label,i)=><span key={label} style={{width:204,textAlign:'center',color:[richPalette.blue,richPalette.teal,richPalette.gold][i]}}>{label}</span>)}</div>
  </>:null}
  {kind==='pricing-flow'?<>
   {node(0,215,347,410,124,31,false)}
   <svg style={{position:'absolute',left:95,top:467}} width={650} height={220} viewBox="0 0 650 220" aria-hidden>
    {[1,2,3].map((i)=><g key={i} opacity={reveal(nodes[i]?.cue??0)}><path d={`M325 1V25H${104+(i-1)*220}V61`} fill="none" stroke={c(i)} strokeWidth="2.4"/><circle cx={104+(i-1)*220} cy={61} r="4" fill={c(i)}/><path d={`M${104+(i-1)*220} 182V205H325V219`} fill="none" stroke={c(i)} strokeWidth="2.4" opacity={reveal(nodes[4]?.cue??0)}/></g>)}
   </svg>
   {[1,2,3].map(i=>node(i,95+(i-1)*220,527,210,122,27,false))}
   {node(4,215,685,410,111,32,false)}
  </>:null}
  {kind==='ai-route'?<>
   <svg style={{position:'absolute',left:95,top:355}} width={650} height={415} viewBox="0 0 650 415" aria-hidden>{arrow(308,82,339,82,nodes[1]?.cue??0,c(1),'a')}{arrow(493,167,493,206,nodes[2]?.cue??0,c(2),'b')}{arrow(338,293,305,293,nodes[3]?.cue??0,c(3),'c')}</svg>
   {node(0,95,350,300,176,34)}{node(1,435,350,310,176,34)}
   {node(3,95,567,300,181,34)}{node(2,435,567,310,181,34)}
  </>:null}
  {kind==='pricing-modes'?<>
   <svg style={{position:'absolute',left:95,top:350,opacity:reveal(nodes[0]?.cue??0)}} width={650} height={400} viewBox="0 0 650 400" aria-hidden><path d="M325 0v400M0 200h650" stroke={richPalette.muted} strokeWidth="2" fill="none"/><circle cx="325" cy="200" r="5" fill={richPalette.blue}/></svg>
   {nodes.slice(0,4).map((n,i)=>node(i,95+(i%2)*336,350+Math.floor(i/2)*210,314,190,32))}
   <div style={{position:'absolute',left:106,top:782,fontSize:25,fontWeight:700,color:richPalette.teal,...enter(conclusionCue)}}>{conclusion}</div>
  </>:null}
  {kind==='refund-compare'?<>
   <svg style={{position:'absolute',left:95,top:350,opacity:reveal(nodes[1]?.cue??0)}} width={650} height={274} viewBox="0 0 650 274" aria-hidden><path d="M324 0v100M324 154v120" stroke={richPalette.muted} strokeWidth="2" fill="none"/></svg>
   <div style={{position:'absolute',left:394,top:463,fontSize:25,fontWeight:700,color:richPalette.gold,...enter(nodes[1]?.cue??0)}}>VS</div>
   {node(0,95,350,306,274,34)}{node(1,437,350,308,274,34)}
   <div style={{position:'absolute',left:98,top:665,width:645,...enter(conclusionCue)}}><div style={{height:3,background:richPalette.gold,width:650*reveal(conclusionCue,20)}}/><div style={{fontSize:31,fontWeight:700,color:richPalette.gold,marginTop:25,lineHeight:1.3,whiteSpace:'pre-line'}}>{conclusion}</div></div>
  </>:null}
  {kind==='export-file'?<>
   <div style={{position:'absolute',left:95,top:350,width:310,height:379,border:`2px solid ${richPalette.teal}`,borderRadius:13,...enter(nodes[0]?.cue??0)}}>
    <div style={{margin:25,display:'flex',alignItems:'center',gap:12,color:richPalette.teal,fontSize:28,fontWeight:700}}><Icon kind="sheet" color={richPalette.teal}/>{nodes[0]?.label}</div>
    <svg width={254} height={204} viewBox="0 0 254 204" style={{margin:'8px 26px'}} aria-hidden><rect x="1" y="1" width="252" height="202" rx="5" stroke={richPalette.teal} strokeWidth="2" fill="none"/>{[36,78,120,162].map(y=><path key={y} d={`M1 ${y}h252`} stroke={richPalette.teal} fill="none" strokeWidth="1.5"/>)}{[84,170].map(x=><path key={x} d={`M${x} 1v202`} stroke={richPalette.teal} fill="none" strokeWidth="1.5"/>)}<path d="M12 19h51M96 19h48M184 19h52" stroke={richPalette.teal} strokeWidth="4"/></svg>
    <div style={{fontSize:22,color:richPalette.muted,margin:'10px 25px'}}>{nodes[0]?.detail}</div>
   </div>
   {node(1,440,365,305,153,31,false)}{node(2,440,559,305,159,31,false)}
  </>:null}
  {kind==='history-reuse'?<>
   <div style={{position:'absolute',left:95,top:370,width:269,height:238,...enter(nodes[0]?.cue??0)}}>
    {[2,1,0].map(i=><div key={i} style={{position:'absolute',left:i*13,top:i*13,width:240,height:206,border:`2px solid ${richPalette.blue}`,borderRadius:12,background:i===0?'transparent':'none'}}/>)}
    <div style={{position:'absolute',left:25,top:27}}><Icon kind="copy" color={richPalette.blue}/><div style={{fontSize:31,fontWeight:700,color:richPalette.blue,marginTop:18}}>{nodes[0]?.label}</div><div style={{fontSize:23,color:richPalette.muted,marginTop:12}}>{nodes[0]?.detail}</div></div>
   </div>
   {node(1,435,370,310,215,32)}
   <svg style={{position:'absolute',left:95,top:356}} width={650} height={355} viewBox="0 0 650 355" aria-hidden><g opacity={reveal(nodes[1]?.cue??0)}><path d="M281 78h51" stroke={richPalette.teal} strokeWidth="2.4"/><path d="M339 78l-10-6v12Z" fill={richPalette.teal}/></g><g opacity={reveal(nodes[2]?.cue??0)}><path d="M496 231v37Q496 300 325 300H137V244" stroke={richPalette.gold} strokeWidth="2.4" fill="none"/><path d="M137 238l-6 10h12Z" fill={richPalette.gold}/></g></svg>
   <div style={{position:'absolute',left:250,top:680,fontSize:30,fontWeight:700,color:richPalette.gold,...enter(nodes[2]?.cue??0)}}>{nodes[2]?.label}</div>
  </>:null}
  {kind==='audience'?<>
   {node(0,95,365,306,241,37)}{node(1,437,365,308,241,37)}
   <svg style={{position:'absolute',left:95,top:606}} width={650} height={96} viewBox="0 0 650 96" aria-hidden><g opacity={reveal(conclusionCue)}><path d="M154 0v37H325V77M497 0v37H325" fill="none" stroke={richPalette.gold} strokeWidth="2.4"/><path d="M325 84l-7-11h14Z" fill={richPalette.gold}/></g></svg>
   <div style={{position:'absolute',left:95,top:717,width:650,fontSize:34,fontWeight:700,lineHeight:1.25,color:richPalette.gold,textAlign:'center',whiteSpace:'pre-line',...enter(conclusionCue)}}>{conclusion}</div>
  </>:null}
  {kind==='source-cta'?<>
   {node(0,95,350,650,149,36)}{node(1,95,555,650,151,36)}
   <svg style={{position:'absolute',left:95,top:499}} width={650} height={56} viewBox="0 0 650 56" aria-hidden>{arrow(325,2,325,49,nodes[1]?.cue??0,richPalette.teal,'cta')}</svg>
  </>:null}
  {conclusion&& !['pricing-modes','refund-compare','audience'].includes(kind)?<div style={{position:'absolute',left:95,top:kind==='pricing-flow'?808:782,width:650,fontSize:25,fontWeight:700,lineHeight:1.25,color:richPalette.gold,whiteSpace:'pre-line',...enter(conclusionCue)}}>{conclusion}</div>:null}
 </AbsoluteFill>;
};
