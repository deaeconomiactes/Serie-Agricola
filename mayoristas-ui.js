/* Presentation only. Does not read or mutate price observations, filters, loaders or calculations. */
(function () {
    'use strict';
    const root=document.getElementById('priceView');
    if(!root)return;
    const initialDocumentTitle=document.title;
    function syncDocumentTitle(){document.title=root.classList.contains('is-active')?'Precios mayoristas · Serie Agrícola':initialDocumentTitle;}
    new MutationObserver(syncDocumentTitle).observe(root,{attributes:true,attributeFilter:['class']});syncDocumentTitle();
    const more=document.getElementById('priceMoreFilters');
    more.addEventListener('keydown',event=>{
        if(event.key==='Escape'){more.open=false;more.querySelector('summary').focus();}
    });
    const nav=[...root.querySelectorAll('[data-price-target]')];
    function syncNavigation(){
        for(const button of nav){const target=document.getElementById(button.dataset.priceTarget);button.disabled=Boolean(target?.hidden);}
    }
    for(const button of nav){
        const target=document.getElementById(button.dataset.priceTarget);
        button.addEventListener('click',()=>{
            if(!target||target.hidden)return;
            if(target instanceof HTMLDetailsElement)target.open=true;
            const focus=target.querySelector('summary,h2,h3')||target;
            if(!focus.matches('summary'))focus.tabIndex=-1;
            target.scrollIntoView({block:'start'});focus.focus({preventScroll:true});
            for(const peer of nav)peer.removeAttribute('aria-current');button.setAttribute('aria-current','location');
        });
        if(target)new MutationObserver(syncNavigation).observe(target,{attributes:true,attributeFilter:['hidden']});
    }
    syncNavigation();
    const movements=document.getElementById('priceMovements');
    const movementCards=['priceIncreaseCard','priceDecreaseCard'].map(id=>document.getElementById(id));
    function syncMovements(){const empty=movementCards.every(card=>card.hidden);if(movements.hidden!==empty)movements.hidden=empty;}
    for(const card of movementCards)new MutationObserver(syncMovements).observe(card,{attributes:true,attributeFilter:['hidden']});
    syncMovements();
    // Chart.js receives only a resize when a previously closed panel becomes visible.
    for(const disclosure of root.querySelectorAll('.sa-price-disclosure'))disclosure.addEventListener('toggle',()=>{
        if(disclosure.open)for(const canvas of disclosure.querySelectorAll('canvas'))window.Chart?.getChart(canvas)?.resize();
    });
    const sources=document.getElementById('priceSources');
    const alerts=document.createElement('p');alerts.id='priceSourceAlerts';alerts.setAttribute('role','status');alerts.hidden=true;sources.before(alerts);
    function syncSourceAlerts(){
        const notices=[...sources.querySelectorAll('.source-update-status--warning:not([hidden]),.source-update-status--error:not([hidden])')].map(node=>[...node.children].map(child=>child.textContent).join(' · '));
        alerts.textContent=notices.join(' · ');alerts.hidden=!notices.length;
    }
    new MutationObserver(syncSourceAlerts).observe(sources,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','class']});syncSourceAlerts();
    const body=document.getElementById('priceTrafficLightBody'),search=document.getElementById('priceDetailSearch');
    const previous=document.getElementById('priceDetailPrevious'),next=document.getElementById('priceDetailNext');
    let page=0;const size=10;
    const normalized=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
    function showRows(){
        const rows=[...body.rows],query=normalized(search.value.trim());const matched=rows.filter(row=>normalized(row.textContent).includes(query));
        const pages=Math.ceil(matched.length/size);page=Math.min(page,Math.max(0,pages-1));
        const visible=new Set(matched.slice(page*size,(page+1)*size));for(const row of rows)row.hidden=!visible.has(row);
        document.getElementById('priceDetailCount').textContent=`${matched.length} de ${rows.length} productos del detalle calculado. La búsqueda sólo afecta esta tabla.`;
        document.getElementById('priceDetailPage').textContent=pages?`${page+1} / ${pages}`:'0 / 0';previous.disabled=page===0;next.disabled=!pages||page>=pages-1;
    }
    search.addEventListener('input',()=>{page=0;showRows();});previous.addEventListener('click',()=>{page--;showRows();});next.addEventListener('click',()=>{page++;showRows();});
    new MutationObserver(()=>{page=0;showRows();}).observe(body,{childList:true});showRows();
})();
