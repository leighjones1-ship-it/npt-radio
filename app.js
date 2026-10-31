const defaults={stream:'https://stream.radiostudio24.com/listen/rs24_87/radio.mp3',
,email:'',news:[{title:'Local news coming soon',detail:'NPT Radio will publish verified community stories here.'}],roads:[{title:'Check current road conditions',detail:'Use the Traffic Wales link for official live traffic information.'}],council:[{title:'Neath Port Talbot Council',detail:'Follow the official council website for verified services, consultations and announcements.'}],events:[{title:'Community events coming soon',detail:'Dates and details will appear once confirmed by organisers.'}],schedule:[{title:'NPT Radio programme schedule',detail:'Presenter times will be announced ahead of launch.'}]};
let data;try{data={...defaults,...JSON.parse(localStorage.getItem('npt-content')||'{}')}}catch{data={...defaults}}
const $=id=>document.getElementById(id);const audio=$('audio');audio.volume=.75;
function safe(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function render(){for(const [key,id] of [['news','newsItems'],['roads','roadItems'],['council','councilItems'],['schedule','scheduleItems']]){$(id).innerHTML=(Array.isArray(data[key])?data[key]:[]).map(x=>`<div class="item"><strong>${safe(x.title)}</strong><small>${safe(x.detail)}</small></div>`).join('')||'<p>No updates yet.</p>'} $('contactDisplay').textContent=data.email?'Email: '+data.email:'';$('status').textContent=data.stream?'Ready to listen':'Stream not connected yet'}render();
function validStream(){try{const u=new URL(data.stream);return u.protocol==='https:'}catch{return false}}
function play(){if(!validStream()){alert('NPT Radio is not broadcasting yet. Add your HTTPS stream URL in the station editor when your hosting is ready.');return}if(audio.paused){if(audio.src!==data.stream)audio.src=data.stream;audio.play().then(()=>{$('play').textContent='Ⅱ';$('status').textContent='Connecting to NPT Radio…'}).catch(()=>{$('status').textContent='Unable to play stream. Check the URL and server.'})}else{audio.pause();$('play').textContent='▶';$('status').textContent='Paused'}}
$('play').onclick=play;$('listenNow').onclick=()=>{if(!validStream()){play();return}window.open(data.stream,'_blank','noopener,noreferrer')};$('volume').oninput=e=>audio.volume=Number(e.target.value)/100;audio.onplaying=()=>{$('status').textContent='LIVE — NPT Radio';$('play').textContent='Ⅱ'};audio.onerror=()=>{$('status').textContent='Stream unavailable';$('play').textContent='▶'};
$('editOpen').onclick=()=>{const password=prompt('Editor access is local-only and not secured. Type EDIT to continue:');if(password!=='EDIT')return;$('editor').classList.add('open');$('streamInput').value=data.stream;$('emailInput').value=data.email;for(const k of ['news','roads','council','events','schedule'])$(k+'Input').value=JSON.stringify(data[k],null,2);$('editor').scrollIntoView({behavior:'smooth'})};$('close').onclick=()=>$('editor').classList.remove('open');$('save').onclick=()=>{try{const updated={stream:$('streamInput').value.trim(),email:$('emailInput').value.trim()};for(const k of ['news','roads','council','events','schedule']){updated[k]=JSON.parse($(k+'Input').value);if(!Array.isArray(updated[k]))throw Error(k+' must be an array')}data=updated;localStorage.setItem('npt-content',JSON.stringify(data));audio.pause();audio.removeAttribute('src');audio.load();render();loadEvents();$('editorMsg').textContent='Saved in this browser. Export your content for backup.'}catch(e){$('editorMsg').textContent='Could not save: '+e.message}};$('export').onclick=()=>{const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='npt-radio-content.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
if('serviceWorker'in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));

// Public event feed is generated on the host by scripts/update_events.py.
// Manually entered events remain available if the feed has no current entries.
async function loadEvents(){
 const status=$('eventsStatus'), target=$('eventItems');
 try{
  const response=await fetch('./events-feed.json',{cache:'no-store'});
  if(!response.ok)throw Error('Feed unavailable');
  const feed=await response.json();

  // Add events from verified public RSS calendars.
  try{
   const rssResponse=await fetch('./rss-events-feed.json',{
    cache:'no-store'
   });

   if(rssResponse.ok){
    const rssFeed=await rssResponse.json();
    const existing=Array.isArray(feed.events)?feed.events:[];
    const rssEvents=Array.isArray(rssFeed.events)?rssFeed.events:[];

    const combined=[...existing,...rssEvents];
    const seen=new Set();

    feed.events=combined.filter(event=>{
     const key=[
      event.date,
      (event.title||'').trim().toLowerCase(),
      (event.location||'').trim().toLowerCase()
     ].join('|');

     if(seen.has(key))return false;
     seen.add(key);
     return true;
    });
   }
  }catch(error){
   console.warn('RSS events unavailable:',error);
  }
  const today=new Date();
  const entries=(Array.isArray(feed.events)?feed.events:[]).filter(e=>e.date && new Date(e.date+'T23:59:59')>=today).sort((a,b)=>a.date.localeCompare(b.date)).slice(0,20);
  if(entries.length){
   target.replaceChildren();
   for(const e of entries){
    const card=document.createElement('div');card.className='item';
    const heading=document.createElement('strong');heading.textContent=e.title||'Local event';card.append(heading);
    const details=document.createElement('small');details.textContent=[e.date,e.time,e.location].filter(Boolean).join(' • ');card.append(details);
    if(e.url){try{const u=new URL(e.url);if(['https:','http:'].includes(u.protocol)){const a=document.createElement('a');a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Event details ↗';card.append(a)}}catch{}}
    target.append(card);
   }
   status.textContent='Upcoming events from configured organisers · Updated '+(feed.updated_at||'recently')+' · Confirm details with the organiser';
  }else{renderManualEvents();status.textContent='No upcoming events in the connected feeds. Check organiser websites for the latest listings.'}
 }catch{renderManualEvents();status.textContent='Automatic event listings are not available yet. Showing station notices.'}
}
function renderManualEvents(){
 $('eventItems').innerHTML=(Array.isArray(data.events)?data.events:[]).map(e=>`<div class="item"><strong>${safe(e.title)}</strong><small>${safe(e.detail)}</small></div>`).join('')||'<p>No events available yet.</p>';
}
loadEvents();
async function loadNews(){
 const target=$('newsItems');
 try{
  const response=await fetch('./news-feed.json',{cache:'no-store'});
  if(!response.ok)throw Error('News feed unavailable');
  const feed=await response.json();
  const items=Array.isArray(feed.events)?feed.events:[];

  if(!items.length)return;

  target.replaceChildren();

  for(const item of items.slice(0,15)){
   const card=document.createElement('div');
   card.className='item';

   const title=document.createElement('strong');
   title.textContent=item.title||'Local news';
   card.append(title);

   const details=document.createElement('small');
   details.textContent=[
    item.source,
    item.published
   ].filter(Boolean).join(' • ');
   card.append(details);

   if(item.description){
    const description=document.createElement('p');
    description.textContent=item.description;
    card.append(description);
   }

   if(item.url){
    try{
     const url=new URL(item.url);
     if(url.protocol==='https:'){
      const link=document.createElement('a');
      link.href=url.href;
      link.target='_blank';
      link.rel='noopener noreferrer';
      link.textContent='Read full story ↗';
      card.append(link);
     }
    }catch{}
   }

   target.append(card);
  }
 }catch(error){
  console.warn('RSS news unavailable:',error);
 }
}

loadNews();
