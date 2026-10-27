/* Presentation adapter: existing quantity filters, calculations, source rows and charts stay owned by app.js. */
(()=>{
    'use strict';
    const root=document.getElementById('quantityView'),$=id=>document.getElementById(id);
    if(!root)return;
    const main=document.createElement('div');main.className='qt-main';while(root.firstChild)main.append(root.firstChild);
    const rail=document.createElement('details');rail.className='qt-rail';rail.open=true;
    rail.innerHTML='<summary>Análisis de cantidades</summary><div><p class="qt-eyebrow">Análisis</p><nav aria-label="Análisis de cantidades"><button data-qty-target="quantitySummary" aria-current="location">Resumen</button><button data-qty-target="quantityProducts">Productos</button><button data-qty-target="quantityOrigins">Procedencias</button><button data-qty-target="quantitySeasonality">Patrón mensual</button></nav><p class="qt-eyebrow">Consulta</p><nav aria-label="Consulta de cantidades"><button data-qty-target="quantityMethodology">Metodología</button><button data-qty-target="quantityRecords">Detalle de registros</button><button data-qty-target="quantityRecords">Descargas</button></nav><p class="qt-rail-note">Volumen · composición · cambio<br>Registros de la cobertura disponible.</p></div>';
    root.append(rail,main);
    const header=document.createElement('header');header.id='quantitySummary';header.className='qt-header';
    header.innerHTML='<div class="qt-header-top"><span class="qt-eyebrow">Cantidades / Volumen frutihortícola</span><span class="qt-static">Fuente estática</span></div><h2>Cantidades transadas</h2><p id="quantitySelection"></p><p id="quantityCoverage"></p><p class="qt-source">Fuente: registro frutihortícola integrado · Actualización no informada</p>';
    main.prepend(header);
    const filters=main.querySelector('.filters-section'),inner=filters.querySelector('.filters-inner');
    const more=document.createElement('details');more.id='quantityMoreFilters';more.className='qt-more';more.innerHTML='<summary>Más filtros</summary><div></div>';
    for(const id of ['filterYear','filterSerie','filterEspecie','filterOrigen','filterFrequency','filterDestino','filterMunicipio']){
        const control=$(id),label=control.closest('.filter-group').querySelector('label');label.htmlFor=id;
    }
    $('filterSerie').closest('.filter-group').querySelector('label').textContent='Rubro';
    $('filterEspecie').closest('.filter-group').querySelector('label').textContent='Producto';
    $('filterOrigen').closest('.filter-group').querySelector('label').textContent='Procedencia';
    for(const id of ['filterYear','filterSerie','filterEspecie','filterOrigen','filterFrequency'])inner.append($(id).closest('.filter-group'));
    for(const id of ['filterDestino','filterMunicipio'])more.lastElementChild.append($(id).closest('.filter-group'));
    inner.querySelector('.unit-indicator').hidden=true;inner.append(more);
    header.after(filters);
    const legacy=document.createElement('div');legacy.hidden=true;legacy.id='quantityLegacy';main.append(legacy);
    legacy.append(main.querySelector('.kpi-section'));
    const note=main.querySelector('.quantity-method-note');
    const kpis=document.createElement('section');kpis.className='qt-kpis';kpis.setAttribute('aria-label','Indicadores de volumen');
    kpis.innerHTML=[['Volume','Volumen transado','TN de la selección'],['Leader','Producto principal','Participación en el volumen'],['Top5','Concentración Top 5','Productos de la selección']].map(([id,label,desc])=>`<article><span class="qt-kpi-label">${label}</span><strong id="quantity${id}">–</strong><span id="quantity${id}Note">${desc}</span></article>`).join('');
    const comparison=document.createElement('p');comparison.className='qt-comparison';comparison.textContent='Variación interanual: sin base comparable acreditada.';comparison.title='La fuente no acredita una cobertura y metodología anual equivalentes. Ver Metodología.';
    const counts=document.createElement('p');counts.id='quantityCounts';counts.className='qt-counts';
    filters.after(kpis,counts,comparison);
    const card=id=>$(id).closest('.chart-card');
    const analysis=document.createElement('section');analysis.className='qt-analysis';analysis.id='quantityAnalysis';
    const evolution=card('chartMonthly'),products=card('chartTop10');products.id='quantityProducts';
    analysis.append(evolution,products);comparison.after(analysis);
    const originalTitle=$('quantityTimeSeriesTitle');originalTitle.classList.add('qt-canonical');
    const evolutionTitle=document.createElement('h2');evolutionTitle.className='chart-title';evolutionTitle.textContent='Evolución del volumen';originalTitle.after(evolutionTitle);
    evolution.querySelector('.chart-desc').textContent='TN por período · Frutas y hortalizas · Selección y fuente indicadas en el encabezado';
    products.querySelector('.chart-title').textContent='Productos con mayor volumen';products.querySelector('.chart-desc').textContent='Top 10 productos · Volumen observado en TN';
    const composition=document.createElement('section');composition.className='qt-composition';composition.id='quantityComposition';
    legacy.append(card('chartSeriesMonthly'));
    composition.innerHTML='<article class="chart-card"><div class="chart-header"><h2 class="chart-title">Composición mensual por rubro</h2><p class="chart-desc" id="quantityCompositionNote">Participación de frutas y hortalizas en el volumen observado</p></div><div class="chart-body"><canvas id="quantityCompositionChart"></canvas></div></article>';
    analysis.after(composition);
    const origins=document.createElement('section');origins.id='quantityOrigins';origins.className='qt-origins';
    origins.innerHTML='<article class="chart-card"><div class="chart-header"><h2 class="chart-title">Procedencias con mayor volumen</h2><p class="chart-desc">Top 10 · Volumen y participación de la selección</p></div><div class="qt-origin-canvas"><canvas id="quantityOriginChart"></canvas></div></article><aside class="qt-insight"><span class="qt-eyebrow">Concentración observada</span><h3 id="quantityOriginLeader">–</h3><p id="quantityOriginShare"></p><p id="quantityOriginCount"></p><p>Procedencia y destino son dimensiones distintas. No se infiere abastecimiento ni causalidad.</p></aside>';
    composition.after(origins);
    const seasonality=card('heatmapContainer');seasonality.id='quantitySeasonality';
    seasonality.querySelector('.chart-title').textContent='Patrón mensual observado';seasonality.querySelector('.chart-desc').textContent='Producto × mes · Cobertura disponible; no acredita estacionalidad estructural';
    origins.after(seasonality);
    const varieties=document.createElement('details');varieties.className='qt-disclosure';varieties.innerHTML='<summary>Ampliar variedades por volumen</summary>';varieties.append(card('chartVarieties'));seasonality.after(varieties);
    for(const id of ['chartMarket','chartMarketMonthly','chartSpeciesDonut','seasonalityTable'])legacy.append(card(id));
    const oldGrid=main.querySelector('.charts-section');oldGrid.remove();
    const records=document.createElement('details');records.id='quantityRecords';records.className='qt-disclosure';
    records.innerHTML='<summary>Ver detalle de registros</summary><div class="qt-record-tools"><label for="quantityRecordSearch">Buscar en la selección<input type="search" id="quantityRecordSearch" placeholder="Producto, procedencia o fecha"></label><button id="quantityDownload" type="button">Descargar selección CSV</button></div><p id="quantityRecordCount" role="status"></p><div class="qt-record-scroll"><table><thead><tr><th>Fecha</th><th>Producto</th><th>Procedencia</th><th>Volumen</th><th>Unidad</th><th>Detalle</th></tr></thead><tbody id="quantityRecordBody"></tbody></table></div><div class="qt-pages"><button type="button" id="quantityPrevious">Anterior</button><span id="quantityPage"></span><button type="button" id="quantityNext">Siguiente</button></div><details class="qt-technical"><summary>Detalle técnico del registro</summary><pre id="quantityTechnical">Seleccioná un registro en la tabla.</pre></details>';
    varieties.after(records);
    const methodology=document.createElement('details');methodology.id='quantityMethodology';methodology.className='qt-disclosure';methodology.innerHTML='<summary>Metodología, fuente y límites</summary>';
    methodology.append(note);methodology.insertAdjacentHTML('beforeend','<p>Fuente estática: REGISTRO 2025 INTEGRADO.csv. Se conserva el procesamiento y la unidad TN del dashboard. No se atribuye fecha de captura o actualización.</p><p>Top 5 = volumen de los cinco productos con mayor volumen / volumen total × 100. La participación principal usa el mismo denominador. Son medidas descriptivas, no índices sintéticos.</p><p>La cobertura 2024–2025 permite describir un perfil mensual observado. No se certifican cobertura exhaustiva ni estabilidad estacional; no se calcula una variación interanual sin base metodológica acreditada.</p><p>No se agrega un filtro mensual nuevo: año y frecuencia mantienen la lógica de selección existente. Las tablas muestran los registros ya interpretados por el módulo, sin reconstruir valores de origen.</p>');
    records.after(methodology);
    let originChart,compositionChart,lastRows,lastFrequency,page=0,matched=[];
    const date=r=>`${r.year}-${String(r.month).padStart(2,'0')}-${String(r.day).padStart(2,'0')}`;
    const normalized=value=>String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
    const pct=value=>Number.isFinite(value)?`${value.toLocaleString('es-AR',{maximumFractionDigits:1})}%`:'Sin datos';
    function showRecords(){
        const query=normalized($('quantityRecordSearch').value.trim());
        matched=filteredData.filter(r=>normalized([date(r),r.especie,r.origen,r.variedad,r.mercado,r.municipio].join(' ')).includes(query));
        const pages=Math.ceil(matched.length/10);page=Math.max(0,Math.min(page,pages-1));const body=$('quantityRecordBody');body.replaceChildren();
        for(const r of matched.slice(page*10,page*10+10)){
            const tr=document.createElement('tr');for(const value of [date(r),formatLabel(r.especie),r.origen,formatNumber(r.peso),r.unidad]){const td=document.createElement('td');td.textContent=value;tr.append(td);}
            const td=document.createElement('td'),button=document.createElement('button');button.type='button';button.textContent='Ver';button.setAttribute('aria-label',`Detalle de ${r.especie}, ${date(r)}`);button.addEventListener('click',()=>{$('quantityTechnical').textContent=JSON.stringify({archivo:'REGISTRO 2025 INTEGRADO.csv',registro_interpretado:r},null,2);records.querySelector('.qt-technical').open=true;});td.append(button);tr.append(td);body.append(tr);
        }
        $('quantityRecordCount').textContent=`${matched.length.toLocaleString('es-AR')} de ${filteredData.length.toLocaleString('es-AR')} registros de la selección · 10 por página`;
        $('quantityPage').textContent=pages?`${page+1} / ${pages}`:'0 / 0';$('quantityPrevious').disabled=page===0;$('quantityNext').disabled=!pages||page>=pages-1;
    }
    $('quantityRecordSearch').addEventListener('input',()=>{page=0;showRecords();});$('quantityPrevious').addEventListener('click',()=>{page--;showRecords();});$('quantityNext').addEventListener('click',()=>{page++;showRecords();});
    $('quantityDownload').addEventListener('click',()=>{
        const quote=value=>'"'+String(value??'').replace(/"/g,'""')+'"';
        const csv=[['Fecha','Producto','Procedencia','Volumen','Unidad','Destino','Variedad','Municipio','Rubro'],...filteredData.map(r=>[date(r),r.especie,r.origen,r.peso,r.unidad,r.mercado,r.variedad,r.municipio,r.serie])].map(row=>row.map(quote).join(';')).join('\r\n');
        const link=document.createElement('a');link.href=URL.createObjectURL(new Blob(['\uFEFF'+csv],{type:'text/csv;charset=utf-8'}));link.download='cantidades-seleccion.csv';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
    });
    function sync(){
        if(typeof filteredData==='undefined'||!filteredData.length){
            for(const id of ['quantityVolume','quantityLeader','quantityTop5','quantityOriginLeader'])$(id).textContent='Sin registros';
            $('quantityCoverage').textContent='TN · Sin registros para la selección';$('quantityCounts').textContent='0 productos · 0 procedencias';
            for(const id of ['quantityVolumeNote','quantityLeaderNote','quantityOriginShare','quantityOriginCount'])$(id).textContent='Sin datos';
            originChart?.destroy();compositionChart?.destroy();originChart=null;compositionChart=null;lastRows=null;
            if(records.open)showRecords();records.querySelector('.qt-technical').open=false;$('quantityTechnical').textContent='Seleccioná un registro de esta selección.';return;
        }
        $('quantityVolume').textContent=$('totalProduction').textContent;
        $('quantitySelection').textContent=`${$('filterYear').selectedOptions[0].text} · ${$('filterEspecie').selectedOptions[0].text} · Procedencia: ${$('filterOrigen').selectedOptions[0].text}`;
        const dates=filteredData.map(date).sort();$('quantityCoverage').textContent=`TN · ${$('filterFrequency').selectedOptions[0].text} · Último dato: ${dates.at(-1)} · Cobertura seleccionada: ${dates[0]} — ${dates.at(-1)}`;
        if(lastRows===filteredData&&lastFrequency===quantityFrequency)return;lastRows=filteredData;lastFrequency=quantityFrequency;
        const stats=QuantityAnalytics.describe(filteredData);$('quantityVolumeNote').textContent=`${filteredData.length.toLocaleString('es-AR')} registros observados`;
        $('quantityLeader').textContent=stats.products[0]?formatLabel(stats.products[0].name):'Sin datos';$('quantityLeaderNote').textContent=stats.products[0]?`${pct(stats.products[0].share)} · ${formatWeight(stats.products[0].value)}`:'Sin unidad compatible';
        $('quantityTop5').textContent=pct(stats.top5);$('quantityTop5Note').textContent='Participación del volumen de productos';
        $('quantityCounts').textContent=`${stats.products.length} productos · ${stats.origins.length} categorías de procedencia · TN`;
        $('quantityOriginLeader').textContent=stats.origins[0]?.name||'Sin datos';$('quantityOriginShare').textContent=stats.origins[0]?`${pct(stats.origins[0].share)} del volumen · ${formatWeight(stats.origins[0].value)}`:'';$('quantityOriginCount').textContent=`${stats.origins.length} categorías en la selección; incluye etiquetas no informadas`;
        originChart?.destroy();const ranked=stats.origins.slice(0,10);
        originChart=new Chart($('quantityOriginChart'),{type:'bar',data:{labels:ranked.map(r=>r.name),datasets:[{label:'TN',data:ranked.map(r=>r.value),backgroundColor:'#60a5fa',borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',plugins:{legend:{display:false},datalabels:{display:false},tooltip:{callbacks:{label:c=>`${formatWeight(ranked[c.dataIndex].value)} · ${pct(ranked[c.dataIndex].share)}`}}},scales:{x:{ticks:{color:'#a7b8c9',callback:v=>formatNumber(v)},grid:{color:'#ffffff08'}},y:{ticks:{color:'#a7b8c9'}}}}});
        const ranking=Chart.getChart($('chartTop10'));if(ranking){ranking.options.scales.x.ticks.maxTicksLimit=4;ranking.options.scales.y.ticks.font.size=10;ranking.options.scales.y.ticks.callback=function(v){const full=String(this.getLabelForValue(v));return full.length>28?full.slice(0,27)+'…':full;};ranking.update('none');}
        const original=Chart.getChart($('chartSeriesMonthly'));
        if(original){
            const source=original.data.datasets,values=QuantityAnalytics.shares(source.map(d=>d.data));compositionChart?.destroy();
            $('quantityCompositionNote').textContent=selectedYear==='TODOS'?'% del volumen por rubro · Meses combinados de los años seleccionados':'Participación mensual del volumen (%) · '+selectedYear;
            compositionChart=new Chart($('quantityCompositionChart'),{type:'bar',data:{labels:[...original.data.labels],datasets:source.map((d,i)=>({label:d.label,data:values[i],backgroundColor:i?'#66d4b0':'#60a5fa'}))},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#a7b8c9',usePointStyle:true}},datalabels:{display:false},tooltip:{callbacks:{label:c=>`${source[c.datasetIndex].label}: ${pct(c.raw)} · ${formatWeight(source[c.datasetIndex].data[c.dataIndex])}`}}},scales:{x:{stacked:true,ticks:{color:'#a7b8c9'},grid:{display:false}},y:{stacked:true,min:0,max:100,ticks:{color:'#a7b8c9',callback:v=>`${v}%`},grid:{color:'#ffffff08'}}}}});
        }
        page=0;records.querySelector('.qt-technical').open=false;$('quantityTechnical').textContent='Seleccioná un registro de esta selección.';if(records.open)showRecords();
    }
    records.addEventListener('toggle',()=>{if(records.open)showRecords();});
    let pending=false;function schedule(){if(pending)return;pending=true;queueMicrotask(()=>{pending=false;sync();});}
    new MutationObserver(schedule).observe($('totalProduction'),{childList:true,subtree:true,characterData:true});
    new MutationObserver(schedule).observe($('seasonalityTable'),{childList:true});
    const breakpoint=matchMedia('(max-width:700px)');const resizeRail=()=>rail.open=!breakpoint.matches;breakpoint.addEventListener('change',resizeRail);resizeRail();
    for(const button of rail.querySelectorAll('button'))button.addEventListener('click',()=>{
        const target=$(button.dataset.qtyTarget);if(target instanceof HTMLDetailsElement)target.open=true;target.scrollIntoView({block:'start'});const focus=target.querySelector('summary,h2')||target;focus.tabIndex=-1;focus.focus({preventScroll:true});for(const peer of rail.querySelectorAll('button'))peer.removeAttribute('aria-current');button.setAttribute('aria-current','location');
    });
    for(const detail of root.querySelectorAll('details'))detail.addEventListener('keydown',event=>{if(event.key==='Escape'){detail.open=false;detail.querySelector('summary').focus();}});
    varieties.addEventListener('toggle',()=>{if(varieties.open)Chart.getChart($('chartVarieties'))?.resize();});
    const initialTitle=document.title;let wasActive=false;
    const syncTitle=()=>{const active=root.classList.contains('is-active');if(active)document.title='Cantidades transadas · Serie Agrícola';else if(wasActive&&document.title==='Cantidades transadas · Serie Agrícola')document.title=initialTitle;wasActive=active;};
    new MutationObserver(syncTitle).observe(root,{attributes:true,attributeFilter:['class']});document.addEventListener('click',event=>{if(event.target.closest('.module-tab'))queueMicrotask(syncTitle);});syncTitle();schedule();
})();
