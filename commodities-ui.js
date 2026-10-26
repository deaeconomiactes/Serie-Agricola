/* Presentation adapter. Reads prepared views; never writes observations, source state or chart datasets. */
(() => {
    'use strict';
    const root = document.getElementById('commodityView');
    if (!root) return;
    const $ = id => document.getElementById(id);
    const section = $('commoditiesSection');
    const families = [
        ['magyp_internal','Precio interno MAGyP'], ['magyp_board','Pizarra / Cámara'],
        ['magyp_fas','FAS'], ['magyp_fob','FOB'], ['magyp_futures','Futuros externos'], ['sio','SIO Granos']
    ];
    const rail = document.createElement('details');
    rail.className = 'co-rail'; rail.open = true;
    rail.innerHTML = '<summary>Referencias de Commodities</summary><div class="co-rail-body"><p class="co-eyebrow">Familias de referencia</p><nav aria-label="Familias de Commodities">' + families.map(([key,label]) => `<button type="button" data-co-family="${key}">${label}</button>`).join('') + '</nav><p class="co-eyebrow">Contexto y trazabilidad</p><nav aria-label="Contexto de Commodities"><button type="button" data-co-target="commodityMethodology">Metodología</button><button type="button" data-co-target="commoditySources">Fuentes</button><button type="button" data-co-target="commodityHistoryPanel">Series históricas</button><button type="button" data-co-target="commodityObservations">Descargas y detalle</button></nav><p class="co-rail-note">Cada referencia conserva su mercado, moneda y metodología.<br><strong>Sin equivalencias implícitas.</strong></p></div>';
    const main = document.createElement('div'); main.className = 'co-main';
    while (section.firstChild) main.append(section.firstChild);
    section.append(rail, main);
    const heading = main.querySelector('.commodities-heading');
    heading.querySelector('.section-eyebrow').textContent = 'Commodities agrícolas / Referencias de precio';
    heading.querySelector('.commodities-title').remove();
    $('commoditySourceSubtitle').setAttribute('role','heading'); $('commoditySourceSubtitle').setAttribute('aria-level','2');
    const identity = document.createElement('p'); identity.className = 'co-identity'; identity.id = 'commodityIdentity';
    $('commoditySourceSubtitle').after(identity);
    const metadata = document.createElement('p'); metadata.id = 'commodityIdentityMeta'; metadata.className = 'co-identity-meta'; identity.after(metadata);
    const sourceDetails = document.createElement('details'); sourceDetails.id = 'commoditySources'; sourceDetails.className = 'co-disclosure';
    sourceDetails.innerHTML = '<summary>Fuentes, cobertura y actualización</summary><div class="co-source-content"></div>';
    const sourceContent = sourceDetails.lastElementChild;
    ['commodityDataFreshness','commodityDataLastOperation','commodityDataOperationRange','commodityHistoryCoverage'].forEach(id => sourceContent.append($(id)));
    heading.append($('commodityUpdateStatus'));
    heading.append($('commodityDataStatus'));
    const filters = main.querySelector('.commodity-filters');
    const more = document.createElement('details'); more.id = 'commodityMoreFilters'; more.className = 'co-more';
    more.innerHTML = '<summary>Más filtros</summary><div class="co-extra-filters"></div>';
    ['commodityFilterSource','commodityFilterUnit','commodityFilterType','commodityFilterCondition','commodityFilterOrigin'].forEach(id => more.lastElementChild.append($(id).closest('.filter-group')));
    filters.append(more);
    const hint = $('commodityFilterCommodityHint'); filters.after(hint);
    const scope = $('commodityPriceScope'); hint.after(scope);
    const method = document.createElement('details'); method.id = 'commodityMethodology'; method.className = 'co-disclosure';
    method.innerHTML = '<summary>Metodología y límites de comparación</summary>';
    method.append($('commodityMethodNote'));
    const kpis = main.querySelector('.commodity-kpi-grid');
    const coverage = document.createElement('div'); coverage.className = 'co-coverage';
    coverage.append(main.querySelector('.commodity-kpi-products'),main.querySelector('.commodity-kpi-currency'));
    const operations = main.querySelector('.commodity-kpi-operations'); coverage.append(operations);
    kpis.append(main.querySelector('.commodity-kpi-update'));
    const prompt = document.createElement('div');prompt.className='co-series-prompt';prompt.hidden=true;
    prompt.innerHTML='<span class="co-prompt-label">Valor y variación de una referencia</span><strong>Seleccioná una serie</strong><span>Acotá producto, plaza y condición. La evolución y el ranking conservan las series separadas.</span><button type="button">Elegir commodity</button>';
    kpis.prepend(prompt);prompt.querySelector('button').addEventListener('click',()=>{$('commodityFilterCommodityTrigger').click();$('commodityFilterCommodityTrigger').focus();});
    kpis.after(coverage);
    const charts = main.querySelector('.commodity-charts-grid');
    const volume = $('commodityVolume').closest('.chart-card');
    const history = document.createElement('details'); history.id = 'commodityHistoryPanel'; history.className = 'co-disclosure';
    history.innerHTML = '<summary>Actividad de la selección y variaciones mensuales</summary><div class="co-history-content"></div>';
    history.lastElementChild.append(volume,main.querySelector('.commodity-semaphore-card'));
    const latest = main.querySelector('.commodity-latest-card');
    const observations = document.createElement('details'); observations.id = 'commodityObservations'; observations.className = 'co-disclosure';
    observations.innerHTML = '<summary>Ver detalle de observaciones</summary><div class="co-table-tools"><label for="commodityDetailSearch">Buscar en últimos valores por serie<input id="commodityDetailSearch" type="search" placeholder="Producto, plaza o condición"></label><button type="button" id="commodityDownload">Descargar detalle CSV</button></div><p id="commodityDetailCount" role="status"></p>';
    observations.append(latest);
    observations.insertAdjacentHTML('beforeend','<div class="co-pagination"><button type="button" id="commodityDetailPrevious">Anterior</button><span id="commodityDetailPage"></span><button type="button" id="commodityDetailNext">Siguiente</button></div><p class="co-detail-note">Último valor de cada serie filtrada. La descarga incluye todas las filas de este detalle, sin limitarse a la página visible. No es una exportación del histórico completo.</p><details class="co-technical"><summary>Detalle técnico de la selección</summary><pre id="commodityTechnical"></pre></details>');
    const context = document.createElement('div'); context.id = 'commodityContextNotice'; context.className = 'co-context-notice'; context.setAttribute('role','status');
    const curve = document.createElement('section'); curve.id = 'commodityCurvePanel'; curve.className = 'chart-card co-curve'; curve.hidden = true;
    curve.innerHTML = '<div class="chart-header"><h2 class="chart-title">Curva por vencimiento</h2><p class="chart-desc" id="commodityCurveDescription"></p><label class="co-curve-date" for="commodityCurveDate">Fecha de observación <select id="commodityCurveDate"></select></label></div><div class="co-curve-body"><canvas id="commodityCurve"></canvas></div>';
    charts.after(curve,history,observations,sourceDetails,method);
    kpis.before(context);
    const text = id => $(id).textContent.trim();
    const selected = id => {const control=$(id),option=control.options[control.selectedIndex];return option?.dataset.fullLabel || option?.text || '';};
    const title = document.title;
    let wasActive = false;
    function syncTitle() {const active=root.classList.contains('is-active');if(active)document.title='Commodities agrícolas · Serie Agrícola';else if(wasActive&&document.title==='Commodities agrícolas · Serie Agrícola')document.title=title;wasActive=active;}
    new MutationObserver(syncTitle).observe(root,{attributes:true,attributeFilter:['class']});syncTitle();
    document.addEventListener('click',event=>{
        if(event.target.closest('.module-tab,[data-co-family]'))queueMicrotask(syncTitle);
    });
    for (const button of rail.querySelectorAll('[data-co-family]')) button.addEventListener('click',() => {
        $('commodityFilterSource').value = button.dataset.coFamily;
        $('commodityFilterSource').dispatchEvent(new Event('change',{bubbles:true}));
        if(matchMedia('(max-width:700px)').matches){rail.open=false;rail.querySelector('summary').focus();}
    });
    for (const button of rail.querySelectorAll('[data-co-target]')) button.addEventListener('click',() => {
        const target=$(button.dataset.coTarget);target.open=true;target.querySelector('summary').focus();target.scrollIntoView({block:'start'});
    });
    for (const disclosure of root.querySelectorAll('details')) {
        disclosure.addEventListener('keydown',event => {if(event.key==='Escape'){disclosure.open=false;disclosure.querySelector('summary').focus();}});
        disclosure.addEventListener('toggle',() => {if(disclosure.open)for(const canvas of disclosure.querySelectorAll('canvas'))window.Chart?.getChart(canvas)?.resize();});
    }
    const breakpoint=matchMedia('(max-width:700px)');
    function syncRail(){rail.open=!breakpoint.matches;}breakpoint.addEventListener('change',syncRail);syncRail();
    const body=$('commodityLatestBody');let page=0;
    const normalize=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
    function paginate() {
        const rows=[...body.rows],query=normalize($('commodityDetailSearch').value.trim());
        const matched=rows.filter(row=>normalize(row.textContent).includes(query)),pages=Math.ceil(matched.length/10);
        page=Math.max(0,Math.min(page,pages-1));const visible=new Set(matched.slice(page*10,page*10+10));
        for(const row of rows)row.hidden=!visible.has(row);
        $('commodityDetailCount').textContent=`${matched.length} de ${rows.length} series · 10 filas por página · La búsqueda sólo afecta este detalle.`;
        $('commodityDetailPage').textContent=pages?`${page+1} / ${pages}`:'0 / 0';
        $('commodityDetailPrevious').disabled=page===0;$('commodityDetailNext').disabled=!pages||page>=pages-1;
    }
    $('commodityDetailSearch').addEventListener('input',()=>{page=0;paginate();});
    $('commodityDetailPrevious').addEventListener('click',()=>{page--;paginate();});$('commodityDetailNext').addEventListener('click',()=>{page++;paginate();});
    $('commodityDownload').addEventListener('click',()=>{
        const table=body.closest('table'),quote=value=>'"'+value.replace(/"/g,'""')+'"';
        const csv=[...table.rows].map(row=>[...row.cells].map(cell=>quote(cell.textContent.trim())).join(';')).join('\r\n');
        const link=document.createElement('a');link.href=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));
        link.download=`commodities-${$('commodityFilterSource').value}-ultimos-por-serie.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
    });
    let curveChart,curveKey='',curveIdentity='';
    const labelDetails=document.createElement('details');labelDetails.className='co-disclosure co-label-key';labelDetails.id='commodityLabelKey';
    labelDetails.innerHTML='<summary>Ver etiquetas completas</summary><p class="co-detail-note">Los códigos identifican series de esta selección. Las condiciones, posiciones y procedencias completas se conservan aquí y en los tooltips.</p><dl class="co-selected-labels"></dl><dl class="co-series-labels"></dl>';
    charts.after(labelDetails);
    const labelRegistry=new Map(),styledCharts=new WeakSet();
    const shorten=(value,max=32)=>{
        const clean=String(value||'').replace(/\s+/g,' ').trim();
        if(clean.length<=max)return clean;
        const cut=clean.lastIndexOf(' ',max-1);return clean.slice(0,cut>max/2?cut:max-1).trimEnd()+'…';
    };
    const readable=value=>String(value||'').replace(/HARINA DE SOJA/gi,'Harina soja').replace(/ACEITE (?:DE )?SOJA/gi,'Aceite soja').replace(/CEBADA FORRAJERA/gi,'Cebada forr.').replace(/POSICI[ÓO]N /gi,'Pos. ').replace(/Vencimiento: /g,'').replace(/ · circular /gi,' · circ. ');
    function seriesLabel(full,row,code){
        if(full.length<=32)return readable(full);
        const product=shorten(readable(row?.commodity||full.split(' · ')[0]),18);
        const market=shorten(String(row?.lugar_entrega||row?.mercado||'').replace(/\s*En destino$/i,' (dest.)').replace(/\s*En origen$/i,' (orig.)'),22);
        const position=$('commodityFilterSource').value==='magyp_futures'?String(row?.condicion_comercial||''):'';
        const short=shorten([code,product,position||market].filter(Boolean).join(' · '),46);
        labelRegistry.set(code,{short,full});return short;
    }
    function drawLabelKey(){
        const list=labelDetails.querySelector('.co-series-labels');list.replaceChildren();
        for(const {short,full} of labelRegistry.values()){
            const term=document.createElement('dt'),description=document.createElement('dd');term.textContent=short;description.textContent=full;list.append(term,description);
        }
        labelDetails.hidden=!labelRegistry.size&&!labelDetails.querySelector('.co-selected-labels').children.length;
    }
    function compactControlLabels(){
        const selection=labelDetails.querySelector('.co-selected-labels');selection.replaceChildren();
        $('commodityFilterCommodityTrigger').title=commoditySelectedValues.length?commoditySelectedValues.join(' · '):'Todos los commodities';
        for(const control of root.querySelectorAll('select[id^=commodityFilter]')){
            for(const [index,option] of [...control.options].entries()){
                const full=option.dataset.fullLabel||option.textContent;
                if(full.length<=38)continue;
                option.dataset.fullLabel=full;option.title=full;option.setAttribute('aria-label',full);
                option.textContent=`${index} · ${shorten(readable(full),32)}`;
            }
            control.title=selected(control.id);
            if(control.selectedOptions[0]?.dataset.fullLabel){
                const term=document.createElement('dt'),description=document.createElement('dd');term.textContent=control.labels?.[0]?.textContent||'Selección';description.textContent=selected(control.id);selection.append(term,description);
            }
        }
        labelDetails.hidden=!labelRegistry.size&&!selection.children.length;
    }
    function compactCaption(id,caption){
        const original=$(id);if(!original)return;
        original.classList.add('co-full-label');
        let display=root.querySelector(`[data-co-caption="${id}"]`);
        if(!display){display=document.createElement(original.tagName==='H2'||original.getAttribute('role')==='heading'?'h2':'span');display.className=original.className.replace('co-full-label','')+' co-short-label';display.dataset.coCaption=id;original.after(display);}
        display.textContent=caption;display.title=original.textContent;
    }
    function compactMatrixLabels(){
        for(const [index,row] of [...$('commoditySemaphoreBody').rows].entries()){
            const cell=row.cells[0],full=cell.dataset.fullLabel||cell.textContent;
            if(full.length<=38)continue;
            const parts=full.split(' · '),short=seriesLabel(full,{commodity:parts[0],mercado:parts[1]},`M${index+1}`);
            cell.dataset.fullLabel=full;cell.title=full;cell.setAttribute('aria-label',full);
            if(cell.dataset.shortLabel===short)continue;cell.dataset.shortLabel=short;
            const original=document.createElement('span'),display=document.createElement('span');original.className='co-full-label';original.textContent=full;display.textContent=short;cell.replaceChildren(original,display);
        }
    }
    function styleRanking(){
        const changed=['commodityPriceTrend','commodityRanking','commodityVolume'].some(id=>{const chart=window.Chart?.getChart($(id));return chart&&!styledCharts.has(chart);});
        if(!changed){if(!['commodityPriceTrend','commodityRanking','commodityVolume'].some(id=>window.Chart?.getChart($(id)))){labelRegistry.clear();drawLabelKey();}return;}labelRegistry.clear();
        const trend=window.Chart?.getChart($('commodityPriceTrend'));
        if(trend){
            styledCharts.add(trend);
            trend.options.plugins.legend.labels.generateLabels=function(chart){
                return Chart.defaults.plugins.legend.labels.generateLabels(chart).map(item=>{
                    const row=chart.data.datasets[item.datasetIndex].metadata?.find(Boolean);
                    return {...item,text:seriesLabel(item.text,row,`E${item.datasetIndex+1}`)};
                });
            };
            trend.options.plugins.legend.onHover=(_event,item,legend)=>{legend.chart.canvas.title=legend.chart.data.datasets[item.datasetIndex].label;};
            trend.options.plugins.legend.onLeave=(_event,_item,legend)=>{legend.chart.canvas.title='';};
            trend.update('none');
        }
        for(const [id,prefix] of [['commodityRanking','R'],['commodityVolume','A']]){
            const chart=window.Chart?.getChart($(id));if(!chart)continue;styledCharts.add(chart);
            const labels=chart.data.labels.map((full,index)=>seriesLabel(String(full),chart.data.datasets[0].metadata?.[index],`${prefix}${index+1}`));
            chart.options.scales.y.ticks.callback=value=>{const label=labels[value]||'';const split=label.lastIndexOf(' · ');return label.length>28&&split>0?[label.slice(0,split),label.slice(split+3)]:label;};
            chart.options.scales.y.afterFit=scale=>{scale.width=Math.min(scale.width,155);};
            chart.options.scales.x.ticks.maxTicksLimit=4;chart.options.plugins.legend.display=false;chart.update('none');
        }
        drawLabelKey();
    }
    const maturity = raw => {
        if(/^\d{4}-\d{2}(-\d{2})?$/.test(raw))return raw;
        const months={ENE:'01',FEB:'02',MAR:'03',ABR:'04',MAY:'05',JUN:'06',JUL:'07',AGO:'08',SET:'09',SEP:'09',OCT:'10',NOV:'11',DIC:'12'};
        const match=/^(ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SET|SEP|OCT|NOV|DIC)(\d{4})$/.exec(raw);
        return match?`${match[2]}-${months[match[1]]}`:null;
    };
    function syncCurve() {
        // No synthetic continuous contract: project only published daily observations with an unambiguous ISO maturity.
        const family=$('commodityFilterSource').value;
        if(family!=='magyp_futures'||$('commodityFilterFrequency').value!=='diaria'){curve.hidden=true;return;}
        const all=getCommodityFilteredRows();
        const fields=['commodity','mercado','moneda','unidad','tipo_precio'];
        const compatible=all.length>=2 && fields.every(key=>new Set(all.map(row=>row[key])).size===1)
            && all.every(row=>row.moneda && row.unidad && row.moneda!=='Sin identificar'&&row.unidad!=='Sin identificar'&&maturity(row.condicion_comercial||''));
        if(!compatible){curve.hidden=true;return;}
        const dates=[...new Set(all.map(row=>row.fecha))].sort().reverse(),dateControl=$('commodityCurveDate');
        const identity=fields.map(key=>all[0][key]).join('|');
        const previous=identity===curveIdentity?dateControl.value:'';curveIdentity=identity;
        const dateOptions=dates.join('|');
        if(dateControl.dataset.options!==dateOptions){dateControl.replaceChildren(...dates.map(date=>new Option(date,date)));dateControl.dataset.options=dateOptions;}
        dateControl.value=dates.includes(previous)?previous:dates[0];
        const rows=all.filter(row=>row.fecha===dateControl.value);
        const unique=rows.length>=2 && new Set(rows.map(row=>maturity(row.condicion_comercial))).size===rows.length;
        curve.hidden=!unique;if(!unique)return;
        const ordered=[...rows].sort((a,b)=>maturity(a.condicion_comercial).localeCompare(maturity(b.condicion_comercial)));
        const key=JSON.stringify(ordered);if(key===curveKey)return;curveKey=key;
        curveChart?.destroy();
        $('commodityCurveDescription').textContent=`Observación: ${rows[0].fecha} · ${rows[0].commodity} · ${rows[0].mercado} · ${rows[0].moneda}/${rows[0].unidad}. Eje horizontal: vencimiento; sin roll continuo.`;
        curveChart=new Chart($('commodityCurve'),{type:'line',data:{labels:ordered.map(row=>row.condicion_comercial),datasets:[{label:`${rows[0].moneda}/${rows[0].unidad}`,data:ordered.map(row=>Number(row.precio_mediana)),borderColor:'#60a5fa',pointRadius:4,tension:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#a7b8c9'},title:{display:true,text:'Vencimiento',color:'#a7b8c9'}},y:{ticks:{color:'#a7b8c9'}}}}});
    }
    $('commodityCurveDate').addEventListener('change',syncCurve);
    observations.querySelector('.co-technical').addEventListener('toggle',event=>{
        if(!event.target.open)return;
        $('commodityTechnical').textContent=JSON.stringify(getCommodityLatestRows().map(row=>Object.fromEntries(Object.entries(row).filter(([key])=>/source|capture|captura|flag|hash|schema|series_id|circular|vencimiento/i.test(key)))),null,2);
    });
    function sync() {
        const family=$('commodityFilterSource').value,sio=family==='sio';root.dataset.family=family;
        compactControlLabels();
        compactCaption('commoditySourceSubtitle',families.find(([key])=>key===family)?.[1]||'Commodities');
        compactCaption('commodityKpiMedianLabel',sio?'Mediana de eventos':$('commodityFilterFrequency').value==='diaria'?'Última cotización':'Precio mensual');
        compactCaption('commodityKpiMonthlyLabel',$('commodityFilterFrequency').value==='diaria'?'Var. 7 días':'Var. mensual');
        compactCaption('commodityKpiYoYLabel',$('commodityFilterFrequency').value==='diaria'?'Var. 30 días':'Var. interanual');
        compactCaption('commodityTrendTitle',sio?'Evolución de eventos':'Evolución de la referencia');
        compactCaption('commodityRankingTitle',sio?'Medianas por serie':family==='magyp_fob'?'Referencias por posición':'Últimos valores');
        compactCaption('commodityVolumeTitle',sio?'Volumen informado':'Observaciones publicadas');
        const multiple=text('commodityKpiMedian')==='Seleccioná una serie';root.classList.toggle('co-multiple-series',multiple);prompt.hidden=!multiple;
        for(const button of rail.querySelectorAll('[data-co-family]')){if(button.dataset.coFamily===family)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}
        identity.textContent=`${text('commodityFilterCommoditySummary')} · ${selected('commodityFilterMarket')}${family==='magyp_futures'?($('commodityFilterCondition').value==='TODOS'?' · Vencimientos separados':` · Vencimiento: ${selected('commodityFilterCondition')}`):''}`;
        metadata.textContent=`${selected('commodityFilterCurrency')}/${selected('commodityFilterUnit')} · ${selected('commodityFilterFrequency')}${family==='magyp_internal'?' publicado':sio?' · operaciones/eventos informados':' · referencia por serie'} · Último dato: ${text('commodityKpiUpdate')} · Cobertura seleccionada: ${text('commodityKpiRange')}`;
        if(sio && operations.parentElement!==kpis)kpis.insertBefore(operations,kpis.lastElementChild);
        if(!sio && operations.parentElement!==coverage)coverage.append(operations);
        main.querySelector('.commodity-kpi-monthly').classList.toggle('co-secondary-kpi',sio);
        main.querySelector('.commodity-kpi-yoy').classList.toggle('co-secondary-kpi',sio);
        context.hidden=!['sio','magyp_fob','magyp_futures'].includes(family);
        context.textContent=sio?'SIO · operaciones/eventos informados. Lugar de entrega, procedencia y condiciones permanecen separados; no es precio spot ni precio de plaza.':family==='magyp_fob'?'FOB · Histórico SSPM y publicación API corriente son contextos separados. Tipo de precio, moneda y unidad identifican el contexto activo; no se construye continuidad entre metodologías.':family==='magyp_futures'?'Futuros · La fecha del gráfico es la observación. El vencimiento identifica el contrato y se consulta en Más filtros y en el detalle. No se crea un roll continuo.':'';
        if(observations.querySelector('.co-technical').open)observations.querySelector('.co-technical').open=false;
        styleRanking();compactMatrixLabels();drawLabelKey();syncCurve();
    }
    let queued=false;
    function schedule(){if(queued)return;queued=true;queueMicrotask(()=>{queued=false;sync();});}
    new MutationObserver(()=>{page=0;paginate();schedule();}).observe(body,{childList:true});
    // The existing monthly matrix is also bounded to ten visible series; cell values/states stay intact.
    const matrix=$('commoditySemaphoreBody'),matrixCard=matrix.closest('.chart-card');
    const matrixTools=document.createElement('div');matrixTools.className='co-table-tools';
    matrixTools.innerHTML='<label for="commodityMatrixSearch">Buscar serie en variaciones mensuales<input id="commodityMatrixSearch" type="search"></label>';
    matrixCard.querySelector('.commodity-table-wrap').before(matrixTools);
    const matrixPages=document.createElement('div');matrixPages.className='co-pagination';
    matrixPages.innerHTML='<button type="button">Anterior</button><span role="status"></span><button type="button">Siguiente</button>';matrixCard.append(matrixPages);
    let matrixPage=0;
    function paginateMatrix(){
        const rows=[...matrix.rows],query=normalize($('commodityMatrixSearch').value.trim()),matched=rows.filter(row=>normalize(row.textContent).includes(query));
        const pages=Math.ceil(matched.length/10);matrixPage=Math.max(0,Math.min(matrixPage,pages-1));
        const visible=new Set(matched.slice(matrixPage*10,matrixPage*10+10));for(const row of rows)row.hidden=!visible.has(row);
        matrixPages.querySelector('span').textContent=`${pages?matrixPage+1:0} / ${pages} · ${matched.length} series`;
        matrixPages.firstElementChild.disabled=matrixPage===0;matrixPages.lastElementChild.disabled=!pages||matrixPage>=pages-1;
    }
    $('commodityMatrixSearch').addEventListener('input',()=>{matrixPage=0;paginateMatrix();});
    matrixPages.firstElementChild.addEventListener('click',()=>{matrixPage--;paginateMatrix();});matrixPages.lastElementChild.addEventListener('click',()=>{matrixPage++;paginateMatrix();});
    new MutationObserver(()=>{matrixPage=0;paginateMatrix();}).observe(matrix,{childList:true});paginateMatrix();
    for(const id of ['commoditySourceSubtitle','commodityKpiRange','commodityKpiUpdate','commodityFilterCommoditySummary'])new MutationObserver(schedule).observe($(id),{childList:true,subtree:true,characterData:true});
    root.addEventListener('change',schedule);paginate();sync();
})();
