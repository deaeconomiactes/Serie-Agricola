/* Official meat-sector observations; explicit within-series derivatives, no reconstructed source totals. */
(function (root) {
    'use strict';
    const BASE = 'data/carnes/dashboard/';
    const VERSION = 'carnes-v1';
    const FAMILIES = {slaughter:'Faena bovina', production:'Producción bovina', carcass_weight:'Peso medio'};
    const STATUS_LABELS={UPDATED:'Actualizado',HISTORICAL_ENDED:'Serie histórica finalizada',SOURCE_UNAVAILABLE:'Último dato válido · fuente no disponible',NO_PUBLICATION:'Sin nueva publicación',PIPELINE_ERROR:'Error de actualización',NOT_REPORTED:'Estado no informado'};
    const FREQUENCIES = {monthly:'Mensual', annual:'Anual', year_to_date:'Acumulado publicado'};
    const UNITS = {heads:'cabezas', Cabezas:'cabezas', Toneladas:'toneladas (base de peso no identificada)',
        tonnes_carcass_bone_in:'toneladas res con hueso', kg_carcass_bone_in:'kg res con hueso'};
    const METHODS = {resolution_32_2018_dentition:'Sexo y dentición', pre_2019_weight_sex_categories:'Clasificación anterior por peso y sexo'};
    const MONTHS = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
    const FIELDS = ['observation_id','record_id','source_id','source','source_url','family','metric','species','observation_date',
        'period_end','frequency','category','category_raw','age_class','geography','geography_raw','geography_level','market','table_id',
        'entity_type','entity_id','entity_name','entity_tax_id','entity_activity','currency','unit','unit_raw','weight_basis','value',
        'value_raw','value_status','methodology','quality_flags','source_locator','capture_date','capture_id','raw_sha256','schema_version'];
    const number = value => value === '' || value === null || value === undefined ? null : Number(value);
    const format = value => value === null || !Number.isFinite(value) ? 'Sin dato publicado' : new Intl.NumberFormat('es-AR',{maximumFractionDigits:2}).format(value);
    const unit = row => UNITS[row?.unit] || row?.unit || '';
    const date = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? value.split('-').reverse().join('/') : 'No informada';
    const validDate = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') && Number.isFinite(Date.parse(value+'T00:00:00Z')) && new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
    const caption = row => row.frequency === 'year_to_date' ? `Acumulado enero–${MONTHS[Number(row.period_end.slice(5,7))-1]} ${row.period_end.slice(0,4)}` :
        row.frequency === 'annual' ? `Año completo ${row.observation_date.slice(0,4)}` : `${MONTHS[Number(row.observation_date.slice(5,7))-1]} ${row.observation_date.slice(0,4)}`;
    const isTotal = row => row.entity_type === 'total' || row.entity_type === 'national_total' || ['Total general','TOTAL'].includes(row.category);
    const label = row => `${row.category}${row.age_class ? ' · '+row.age_class : ''}`;
    const dentition = value => String(value || '').normalize('NFC').trim().replace(/\s+/g,' ').toLocaleLowerCase('es');

    function parseCSV(text) {
        const records=[];let row=[],cell='',quoted=false;
        for (let i=0;i<text.length;i++) {
            const c=text[i];
            if (c==='"') { if (quoted && text[i+1]==='"') {cell+='"';i++;} else quoted=!quoted; }
            else if (!quoted && (c===',' || c==='\n')) { row.push(cell);cell='';if(c==='\n'){records.push(row);row=[];} }
            else if (c!=='\r' || quoted) cell+=c;
        }
        if(quoted) throw new Error('CSV incompleto');
        if(cell || row.length){row.push(cell);records.push(row);}
        const headers=records.shift();
        if(!headers || JSON.stringify(headers)!==JSON.stringify(FIELDS)) throw new Error('Schema Carnes desconocido');
        return records.map(values=>{if(values.length!==headers.length)throw new Error('Fila incompleta');return Object.fromEntries(headers.map((key,i)=>[key,values[i]]));});
    }

    function validateRows(rows, entry, descriptor) {
        if(rows.length!==descriptor.rows || !rows.length) throw new Error('Cantidad de registros inválida');
        const seen=new Set();
        for(const row of rows) {
            if(row.schema_version!==VERSION || row.source_id!==entry.source_id || row.source_url!==entry.source_url ||
                row.raw_sha256!==entry.raw_sha256 || row.capture_id!==entry.capture_id || row.family!==descriptor.family ||
                row.frequency!==descriptor.frequency || row.observation_date.slice(0,4)!==descriptor.year ||
                !validDate(row.observation_date) || !validDate(row.period_end) ||
                row.period_end<row.observation_date || !row.unit || !row.currency || !row.source_locator ||
                ['establishment','slaughter_user','user','unlabelled_published_row'].includes(row.entity_type) ||
                !/^[a-f0-9]{64}$/.test(row.observation_id) || !/^[a-f0-9]{64}$/.test(row.record_id) || seen.has(row.observation_id)) throw new Error('Observación Carnes inválida');
            seen.add(row.observation_id);
            if(row.value_status==='missing') {if(row.value!=='')throw new Error('Faltante inconsistente');}
            else if(row.value_status!=='observed' || !/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(row.value) || number(row.value)===null || !Number.isFinite(number(row.value)) || number(row.value)<0) throw new Error('Valor inválido');
            row.flags=JSON.parse(row.quality_flags);
            if(!Array.isArray(row.flags) || row.flags.some(f=>typeof f!=='string'))throw new Error('Flags inválidos');
        }
        return rows;
    }

    class Loader {
        constructor(fetcher=root.fetch?.bind(root)) {this.fetcher=fetcher;this.cache=new Map();this.metrics={bytes:0,requests:[]};}
        async response(path) {
            const response=await this.fetcher(path,{cache:'no-cache'});
            if(!response.ok)throw new Error(`Fuente no disponible (HTTP ${response.status})`);
            const buffer=await response.arrayBuffer();this.metrics.bytes+=buffer.byteLength;this.metrics.requests.push({path,bytes:buffer.byteLength});return buffer;
        }
        async init() {
            if(this.index)return this.index;
            const index=JSON.parse(new TextDecoder().decode(await this.response(BASE+'index.json')));
            if(index.schema_version!==VERSION || !index.sources || !Object.keys(index.sources).length)throw new Error('Índice Carnes inválido');
            for(const [id,entry] of Object.entries(index.sources)) {
                if(entry.source_id!==id || !Array.isArray(entry.files) || !/^https:\/\/(www\.magyp\.gob\.ar|datos\.magyp\.gob\.ar|infra\.datos\.gob\.ar)\//.test(entry.source_url))throw new Error('Origen inválido');
                for(const file of entry.files) if(!/^[a-z0-9_-]+-[a-f0-9]{16}\.csv\.gz$/.test(file.path) || !/^[a-f0-9]{64}$/.test(file.sha256) || file.bytes>5000000)throw new Error('Fragmento inválido');
            }
            this.index=index;
            try {
                const report=JSON.parse(new TextDecoder().decode(await this.response('data/carnes/reports/CARNES_UPDATE_STATUS.json')));
                if(report.schema_version!==VERSION || !report.sources)throw new Error('Metadata inválida');
                this.states=report.sources;
            } catch (_) {this.states={};this.statusUnavailable=true;}
            return index;
        }
        async shard(entry,file) {
            if(!this.cache.has(file.sha256)) {
                const promise=(async()=>{
                    const buffer=await this.response(BASE+file.path);
                    const hash=Array.from(new Uint8Array(await root.crypto.subtle.digest('SHA-256',buffer)),n=>n.toString(16).padStart(2,'0')).join('');
                    if(hash!==file.sha256 || buffer.byteLength!==file.bytes)throw new Error('Hash/tamaño de fragmento inválido');
                    const expanded=new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));
                    const reader=expanded.getReader();let size=0;const chunks=[];
                    while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>45000000){await reader.cancel();throw new Error('Fragmento expandido demasiado grande');}chunks.push(value);}
                    const text=await new Blob(chunks).text();return validateRows(parseCSV(text),entry,file);
                })().catch(error=>{this.cache.delete(file.sha256);throw error;});
                this.cache.set(file.sha256,promise);
            }
            return this.cache.get(file.sha256);
        }
        entries(group) {
            return Object.values(this.index.sources).filter(e=>group==='detail' ? e.source_id.startsWith('magyp_slaughter_') :
                group==='production' ? e.source_id==='magyp_production_current' : group==='sspm' ? e.source_id.startsWith('sspm_40_') : e.source_id==='magyp_indicators_archive');
        }
        descriptors(group,family,frequency,year) {
            const found=[];
            for(const entry of this.entries(group)) for(const file of entry.files)
                if(file.family===family && (!frequency || file.frequency===frequency) && (!year || file.year===String(year))) found.push({entry,file});
            // A current publication wins only when it explicitly covers the same shard.
            return found.filter(x=>!found.some(y=>y!==x && y.entry.source_id==='magyp_slaughter_current' && x.file.year===y.file.year && x.file.frequency===y.file.frequency && x.file.family===y.file.family));
        }
        async load(group,family,frequency,year) {
            const batches=[];
            for(const {entry,file} of this.descriptors(group,family,frequency,year))batches.push(await this.shard(entry,file));
            return batches.flat();
        }
    }

    function canonical(rows,state) {
        return rows.filter(row=>{
            if(!['bovino','bovinos','bovinos_y_bubalinos'].includes(row.species))return false;
            if(state.group==='sspm')return row.metric===(state.family==='slaughter'?'vacunos_cabezas':'vacunos_toneladas');
            if(state.group==='archive')return row.metric==='mean_carcass_weight';
            const categoryTable=state.family+'/category_age'+(state.frequency==='year_to_date'?
                state.family==='carcass_weight'?'/PESO MEDIO DE LA RES POR DENTICION (KG)':'/TOTAL POR EDAD':'');
            return row.metric===(state.family==='slaughter'?'slaughter_heads':state.family==='production'?'carcass_production':'mean_carcass_weight') &&
                (row.table_id===categoryTable || state.family==='slaughter' && row.table_id==='slaughter/province');
        });
    }
    function selectedSeries(rows,state) {
        return canonical(rows,state).filter(row=>{
            if(state.group==='sspm' || state.group==='archive')return isTotal(row);
            if(state.family==='slaughter' && state.category==='TOTAL')return state.province==='Argentina' ?
                (state.frequency!=='monthly' ? row.table_id==='slaughter/province' && row.entity_type==='total' : row.table_id==='slaughter/category_age' && isTotal(row)) :
                row.table_id==='slaughter/province' && row.entity_type==='province' && row.geography===state.province;
            if(state.category==='TOTAL')return isTotal(row);
            return !isTotal(row) && row.category===state.category && row.methodology===state.method && (!state.age || dentition(row.age_class)===dentition(state.age));
        });
    }
    function reconcile(state,changed) {
        if(changed==='province' && state.province!=='Argentina'){state.category='TOTAL';state.age='';}
        if(['category','age'].includes(changed) && state.category!=='TOTAL')state.province='Argentina';
        if(state.family!=='slaughter')state.province='Argentina';
        return state;
    }
    const COMPARABLE=['family','metric','species','table_id','entity_type','geography','category','age_class','currency','unit','weight_basis','methodology','frequency'];
    function yearAgo(row,previous) {
        if(!row || number(row.value)===null || row.frequency==='monthly' && !usable(row))return null;
        const year=Number(row.observation_date.slice(0,4))-1;
        const matches=previous.filter(other=>sameSeries(other,row) && (other.frequency!=='monthly' || usable(other)) && other.observation_date===year+row.observation_date.slice(4) &&
            other.period_end.slice(0,4)===String(year) && other.period_end.slice(5,7)===row.period_end.slice(5,7));
        if(matches.length!==1 || number(matches[0].value)===null || number(matches[0].value)<=0)return null;
        return (number(row.value)/number(matches[0].value)-1)*100;
    }
    function point(rows,state) {
        const filtered=rows.filter(r=>state.frequency!=='monthly' || r.observation_date.slice(5,7)===state.month);
        return filtered.length===1?filtered[0]:null;
    }
    function sourceState(entry,statuses) {
        const raw=statuses?.[entry.source_id]?.status;
        const incident=['SOURCE_UNAVAILABLE','NO_PUBLICATION','PIPELINE_ERROR'].includes(raw)?raw:null;
        const historical=entry.source_lifecycle==='HISTORICAL_ENDED';
        return {status:incident || (historical?'HISTORICAL_ENDED':raw==='NO_OP_ALREADY_CURRENT'?'UPDATED':raw || 'NOT_REPORTED'),historical};
    }
    function classificationRows(rows,state,anchor) {
        if(!anchor)return [];
        const scope=canonical(rows,state).filter(r=>!isTotal(r) && ['category','category_rollup'].includes(r.entity_type) && r.methodology===state.method &&
            r.observation_date===anchor.observation_date && r.period_end===anchor.period_end && !r.metric.endsWith('share'));
        return scope;
    }
    function provincialShare(row,rows) {
        if(!row || row.entity_type!=='province')return null;
        const matches=rows.filter(r=>(row.frequency!=='monthly' ? r.table_id==='slaughter/province' && r.entity_type==='total' : r.table_id==='slaughter/category_age' && isTotal(r)) && r.observation_date===row.observation_date &&
            r.period_end===row.period_end && r.species===row.species && r.unit===row.unit);
        return matches.length===1 && number(row.value)!==null && number(matches[0].value)>0 ? number(row.value)/number(matches[0].value)*100:null;
    }

    // Derived measures retain original rows. Publication lineage is explicit; no source splicing.
    const publication = row => /^magyp_slaughter_(?:current|\d{4})$/.test(row.source_id)?'magyp_slaughter':row.source_id;
    const ANALYTIC_DIMS=[...COMPARABLE,'market','entity_id','entity_name','entity_activity'];
    // Official 2025/2026 dentition labels differ in capitalisation, not in classification.
    // Compare only this label case/spacing-insensitively; keep every original value unchanged.
    const dimensionValue=(row,key)=>key==='age_class'?dentition(row[key]):row[key];
    const sameSeries=(a,b)=>!!a && !!b && publication(a)===publication(b) && ANALYTIC_DIMS.every(k=>dimensionValue(a,k)===dimensionValue(b,k));
    const monthIndex=row=>Number(row.observation_date.slice(0,4))*12+Number(row.observation_date.slice(5,7))-1;
    const usable=row=>row?.frequency==='monthly' && row.value_status==='observed' && number(row.value)!==null && Number.isFinite(number(row.value)) && number(row.value)>=0 &&
        validDate(row.observation_date) && validDate(row.period_end) && row.observation_date.endsWith('-01') && row.period_end===new Date(Date.UTC(Number(row.observation_date.slice(0,4)),Number(row.observation_date.slice(5,7)),0)).toISOString().slice(0,10);
    const sum=rows=>rows.reduce((total,row)=>total+number(row.value),0);
    function monthlyWindow(rows,anchor,count,offset=0) {
        if(!usable(anchor))return null;
        const end=monthIndex(anchor)-offset,result=[];
        for(let i=end-count+1;i<=end;i++){
            const found=rows.filter(r=>sameSeries(r,anchor) && monthIndex(r)===i);
            if(found.length!==1 || !usable(found[0]))return null;result.push(found[0]);
        }return result;
    }
    function derivedYTD(rows,anchor) {
        if(!usable(anchor) || !['slaughter','production'].includes(anchor.family))return null;
        const count=Number(anchor.observation_date.slice(5,7));const current=monthlyWindow(rows,anchor,count),previous=monthlyWindow(rows,anchor,count,12);
        if(!current)return null;const value=sum(current),base=previous?sum(previous):null;
        return {value,base,variation:base>0?(value/base-1)*100:null,count,rows:current,previous:previous || []};
    }
    function rollingReference(rows,anchor) {
        const window=monthlyWindow(rows,anchor,12);if(!window)return null;const mean=sum(window)/12;
        return {mean,difference:number(anchor.value)-mean,percent:mean>0?(number(anchor.value)/mean-1)*100:null,rows:window};
    }
    const reconciles=(rows,total)=>rows.length>0 && rows.every(r=>r.value_status==='observed' && number(r.value)!==null && Number.isFinite(number(r.value)) && number(r.value)>=0) && Math.abs(sum(rows)-number(total.value))<=Math.max(1e-6,Math.abs(number(total.value))*1e-10);
    function publishedDenominator(rows,anchor) {
        if(!anchor)return null;
        const found=rows.filter(r=>r.source_id===anchor.source_id && r.capture_id===anchor.capture_id &&
            ['family','metric','species','currency','unit','weight_basis','frequency','observation_date','period_end'].every(k=>r[k]===anchor[k]) &&
            r.geography==='Argentina' && isTotal(r) && r.table_id===(anchor.frequency==='monthly'?'slaughter/category_age':'slaughter/province'));
        return found.length===1 && found[0].value_status==='observed' && number(found[0].value)>0?found[0]:null;
    }
    function territorialDistribution(rows,anchor) {
        if(!anchor || anchor.family!=='slaughter')return null;const total=publishedDenominator(rows,anchor);if(!total)return null;
        const provinces=rows.filter(r=>r.entity_type==='province' && r.table_id==='slaughter/province' && r.source_id===anchor.source_id && r.capture_id===anchor.capture_id &&
            ['family','metric','species','currency','unit','weight_basis','frequency','observation_date','period_end'].every(k=>r[k]===anchor[k]));
        if(new Set(provinces.map(r=>r.geography)).size!==provinces.length || !reconciles(provinces,total))return null;
        const sorted=[...provinces].sort((a,b)=>number(b.value)-number(a.value) || a.geography.localeCompare(b.geography));
        const items=sorted.map((row,i)=>({row,rank:1+sorted.filter(r=>number(r.value)>number(row.value)).length,share:number(row.value)/number(total.value)*100}));
        return {total,items,top3:items.length>=3?sum(items.slice(0,3).map(i=>i.row))/number(total.value)*100:null};
    }
    function compositionDistribution(rows,state,anchor) {
        if(state.family!=='slaughter' || state.frequency!=='monthly' || state.province!=='Argentina')return null;
        const total=publishedDenominator(rows,anchor);const components=classificationRows(rows,state,anchor);
        if(!total || !components.length || new Set(components.map(r=>r.category+'|'+dimensionValue(r,'age_class'))).size!==components.length)return null;
        if(!components.every(r=>r.source_id===total.source_id && r.capture_id===total.capture_id &&
            ['family','metric','species','currency','unit','weight_basis','frequency','observation_date','period_end'].every(k=>r[k]===total[k])) || !reconciles(components,total))return null;
        return {total,items:components.map(row=>({row,share:number(row.value)/number(total.value)*100}))};
    }
    function compareComposition(current,previous) {
        if(!current || !previous || current.items.length!==previous.items.length)return null;
        const result=current.items.map(item=>{const matches=previous.items.filter(other=>sameSeries(item.row,other.row) &&
            Number(other.row.observation_date.slice(0,4))===Number(item.row.observation_date.slice(0,4))-1 &&
            other.row.observation_date.slice(5)===item.row.observation_date.slice(5) && other.row.period_end.slice(5,7)===item.row.period_end.slice(5,7));
            return matches.length===1?{...item,previous:matches[0].share,previousRow:matches[0].row,pp:item.share-matches[0].share}:null;});
        return result.every(Boolean)?result:null;
    }
    function historicalReference(rows,anchor) {
        if(!usable(anchor))return null;const year=Number(anchor.observation_date.slice(0,4)),years=[];
        for(let y=year-5;y<year;y++){
            const end={...anchor,observation_date:y+'-12-01',period_end:y+'-12-31'};const full=monthlyWindow(rows,end,12);
            if(full)years.push({year:y,rows:full});
        }
        const recent=monthlyWindow(rows,anchor,36,1);
        return {years,seasonality:years.length>=3?MONTHS.map((_,m)=>({mean:years.reduce((v,y)=>v+number(y.rows[m].value),0)/years.length,min:Math.min(...years.map(y=>number(y.rows[m].value))),max:Math.max(...years.map(y=>number(y.rows[m].value)))})):null,
            range:recent?{min:Math.min(...recent.map(r=>number(r.value))),max:Math.max(...recent.map(r=>number(r.value))),rows:recent}:null};
    }
    const Analytics={publication,sameSeries,monthlyWindow,derivedYTD,rollingReference,publishedDenominator,territorialDistribution,compositionDistribution,compareComposition,historicalReference};

    function element(tag,className,text) {const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
    function select(parent,id,title,options) {
        const group=element('div','filter-group');const labelNode=element('label','filter-label',title);labelNode.htmlFor=id;
        const input=element('select','filter-select');input.id=id;group.append(labelNode,input);parent.append(group);
        setOptions(input,options);return input;
    }
    function setOptions(input,options,value) {
        input.replaceChildren();for(const [key,text] of options){const option=element('option','',text);option.value=key;input.append(option);}
        input.value=options.some(([key])=>key===value)?value:options[0]?.[0] || '';
    }
    function card(parent,title) {
        const node=element('div','kpi-card');const content=element('div','kpi-content');
        const heading=element('span','kpi-label',title);const value=element('span','kpi-value','Sin dato publicado');const note=element('span','kpi-unit');content.append(heading,value,note);node.append(content);parent.append(node);return {node,heading,value,note};
    }
    function chartCard(parent,title) {
        const node=element('div','chart-card');const header=element('div','chart-header');const heading=element('h3','chart-title',title);const desc=element('p','chart-desc');header.append(heading,desc);
        const body=element('div','chart-body carnes-chart');const canvas=element('canvas');canvas.setAttribute('role','img');canvas.setAttribute('aria-label',title);body.append(canvas);
        const empty=element('p','carnes-empty');empty.hidden=true;node.append(header,body,empty);parent.append(node);return {node,heading,desc,canvas,body,empty};
    }

    class View {
        constructor(container,loader=new Loader()) {this.container=container;this.loader=loader;this.revision=0;this.referenceRevision=0;this.charts=new Map();
            this.state={family:'slaughter',group:'detail',frequency:'monthly',year:'',month:'',province:'Argentina',category:'TOTAL',age:'',method:'resolution_32_2018_dentition'};}
        async mount() {
            this.container.replaceChildren();this.notice=element('p','carnes-notice','Cargando datos oficiales…');this.notice.setAttribute('role','status');this.container.append(this.notice);
            try {await this.loader.init();this.build();await this.update('family');}
            catch(error){this.notice.textContent='No se pudo cargar Carnes: '+error.message;const retry=element('button','filter-select','Reintentar');retry.type='button';retry.onclick=()=>this.mount();this.container.append(retry);}
        }
        build() {
            const shell=element('div','carnes-shell');this.container.append(shell);
            const rail=element('aside','carnes-rail');rail.setAttribute('aria-label','Navegación contextual de Carnes');const c=element('main','carnes-main');shell.append(rail,c);
            const glyph=name=>{const node=element('span','carnes-glyph');node.setAttribute('aria-hidden','true');node.style.maskImage=`url(assets/carnes/icons/${name}.svg)`;node.style.webkitMaskImage=node.style.maskImage;return node;};
            rail.append(element('p','carnes-rail-label','Carnes'));
            const overview=element('header','carnes-overview');c.append(overview);const heading=element('div','carnes-heading');const moduleTitle=c.closest('.prices-section').querySelector('#carnesTitle');this.familyTitle=element('h2','carnes-family-title');this.badge=element('span','source-update-status__badge');heading.append(moduleTitle,element('span','carnes-heading-divider','/'),this.familyTitle,this.badge);overview.append(heading);heading.prepend(glyph('cow'));
            this.metadata=element('div','carnes-metadata');this.metaText=element('div','carnes-meta-items');this.sourceLink=element('a','','Ver fuente institucional');this.sourceLink.target='_blank';this.sourceLink.rel='noopener noreferrer';this.metadata.append(this.metaText);overview.append(this.metadata);
            const context=element('div','carnes-context');c.append(context);const nav=element('nav','carnes-family-nav');nav.setAttribute('aria-label','Familias de Carnes');this.familyButtons=new Map();
            for(const [key,title] of Object.entries(FAMILIES)){const button=element('button','',title);button.type='button';button.onclick=()=>{this.state.family=key;reconcile(this.state,'family');this.update('family');};nav.append(button);this.familyButtons.set(key,button);}rail.append(nav);for(const [key,button] of this.familyButtons){button.prepend(glyph(key==='carcass_weight'?'scales':key==='production'?'database':'cow'));}rail.append(element('p','carnes-rail-label','Fuentes y consulta'),this.sourceLink);
            const toolbar=element('div','carnes-toolbar');context.append(toolbar);const filters=element('div','filters-grid carnes-filters');filters.setAttribute('aria-label','Filtros de Carnes');toolbar.append(filters);this.controls={};
            this.contextFilters=element('details','carnes-context-filters');this.contextSummary=element('summary','','Más filtros');this.contextFilters.append(this.contextSummary);const contextual=element('div','filters-grid');this.contextFilters.append(contextual);toolbar.append(this.contextFilters);
            this.contextFilters.addEventListener('keydown',event=>{if(event.key==='Escape'){this.contextFilters.open=false;this.contextSummary.focus();}});
            for(const [key,title] of [['family','Familia'],['year','Año'],['month','Mes'],['frequency','Frecuencia'],['group','Fuente'],['province','Provincia'],['category','Categoría'],['age','Dentición'],['method','Clasificación'],['species','Especie']]) {
                const input=select(['province','category','age','method','species'].includes(key)?contextual:filters,'carnes-'+key,title,[]);this.controls[key]=input;
                if(key!=='species')input.addEventListener('change',()=>{this.state[key]=input.value;reconcile(this.state,key);this.update(key);});
            }
            this.controls.family.parentElement.hidden=true;this.controls.species.disabled=true;this.controls.species.parentElement.hidden=true;
            const methodology=element('details','carnes-methodology');methodology.append(element('summary','','Contexto y metodología de la selección'));this.methodNote=element('p','method-note carnes-method');methodology.append(this.methodNote);
            this.analyticsMethod=element('p','method-note carnes-analytics-method');methodology.append(this.analyticsMethod);const methodAction=element('button','carnes-rail-action','Metodología');methodAction.type='button';methodAction.prepend(glyph('file-text'));methodAction.onclick=()=>{methodology.open=true;methodology.scrollIntoView({block:'center'});methodology.querySelector('summary').focus({preventScroll:true});};rail.append(methodAction);
            this.selectionNote=element('p','carnes-selection-note');c.append(this.selectionNote);
            const openObservations=()=>{this.observations.open=true;this.observations.scrollIntoView({block:'start'});this.observations.querySelector('summary').focus({preventScroll:true});};const kpis=element('div','kpi-grid carnes-kpis');c.append(kpis);this.kpis=[card(kpis,'Cabezas'),card(kpis,'Variación interanual'),card(kpis,'Participación provincial'),card(kpis,'Categoría / dentición principal')];for(const [index,kpi] of this.kpis.entries()){const badge=element('span','carnes-kpi-symbol');badge.append(glyph(['chart-bar','percent','calendar','chart-pie-slice'][index]));kpi.node.prepend(badge);}
            this.highlights=element('section','carnes-highlights');this.highlights.append(element('h3','chart-title','Cambios destacados'));this.highlightList=element('ul');this.highlights.append(this.highlightList);this.analyticNote=element('p','chart-desc carnes-analytic-note');c.append(this.analyticNote);
            const analysis=element('div','carnes-analysis');c.append(analysis);this.timeline=chartCard(analysis,'Evolución temporal');const breakdown=element('div','carnes-breakdown');analysis.append(breakdown);this.ranking=chartCard(breakdown,'Ranking provincial');this.composition=chartCard(analysis,'Composición nacional por categoría / dentición');analysis.append(this.highlights);
            this.timeline.node.classList.add('carnes-timeline');this.breakdown=breakdown;this.ranking.node.classList.add('carnes-ranking');this.composition.node.classList.add('carnes-composition');
            this.referenceSection=element('details','carnes-references');this.referenceSection.append(element('summary','','Estacionalidad y rango histórico · misma serie'));this.referenceStatus=element('p','chart-desc');this.referenceSection.append(this.referenceStatus);this.seasonality=chartCard(this.referenceSection,'Estacionalidad mensual');this.heatmap=element('div','carnes-heatmap');this.referenceSection.append(this.heatmap);c.append(this.referenceSection);
            this.referenceSection.addEventListener('toggle',()=>{if(this.referenceSection.open)this.loadReferences();});
            c.append(methodology);this.observations=element('details','carnes-observations');this.observations.append(element('summary','','Ver detalle de observaciones'));c.append(this.observations);this.table=this.makeTable(this.observations,'Detalle de observaciones');this.buildDetail(c);const recordsAction=element('button','carnes-rail-action','Observaciones');recordsAction.type='button';recordsAction.prepend(glyph('list-bullets'));recordsAction.onclick=openObservations;rail.append(recordsAction);
            const details=element('details','chart-card carnes-history');const summary=element('summary','','Series históricas finalizadas');details.append(summary);
            const history=element('div','carnes-history-content');details.append(history);c.append(details);
            history.append(element('p','chart-desc','Liniers 1998–2019 y exportaciones 1998–2019 · Series históricas finalizadas. No representan indicadores corrientes.'));
            const historyAction=element('button','carnes-rail-action','Series finalizadas');historyAction.type='button';historyAction.prepend(glyph('archive'));historyAction.onclick=()=>{details.open=true;details.scrollIntoView({block:'start'});summary.focus({preventScroll:true});};rail.append(historyAction);const railFoot=element('div','carnes-rail-foot');railFoot.append(glyph('database'),element('strong','','Datos institucionales'),element('span','','Observaciones publicadas y trazabilidad de origen'));rail.append(railFoot);this.historyContainer=history;details.addEventListener('toggle',()=>{if(details.open && !this.historyBuilt){this.historyBuilt=true;this.buildHistory();}});
        }
        groups() {return this.state.family==='slaughter' ? [['detail','MAGyP / DNCCA · detalle publicado'],['sspm','SAGyP / SSPM · nacional']] :
            this.state.family==='production' ? [['production','MAGyP / DNCCA · producción'],['sspm','SAGyP / SSPM · nacional']] :
            [['production','MAGyP / DNCCA · peso por categoría'],['archive','MAGyP · indicadores históricos finalizados']];}
        async update(changed) {
            const revision=++this.revision;this.container.setAttribute('aria-busy','true');this.notice.textContent='Cargando selección…';
            try {
                if(changed==='family') {this.state.group=this.groups()[0][0];this.state.category='TOTAL';this.state.age='';this.state.province='Argentina';}
                if(changed==='group'){this.state.category='TOTAL';this.state.age='';this.state.province='Argentina';}
                setOptions(this.controls.family,Object.entries(FAMILIES),this.state.family);setOptions(this.controls.group,this.groups(),this.state.group);
                const available=this.loader.descriptors(this.state.group,this.state.family);
                const frequencies=Object.keys(FREQUENCIES).filter(f=>available.some(x=>x.file.frequency===f));
                if(!frequencies.includes(this.state.frequency))this.state.frequency=frequencies[0];
                setOptions(this.controls.frequency,frequencies.map(f=>[f,FREQUENCIES[f]]),this.state.frequency);
                const years=[...new Set(available.filter(x=>x.file.frequency===this.state.frequency).map(x=>x.file.year))].sort().reverse();
                if(!years.includes(this.state.year) || ['family','group','frequency'].includes(changed))this.state.year=years[0];
                if(!this.state.year)throw new Error('No hay períodos publicados para esta selección');
                setOptions(this.controls.year,years.map(y=>[y,y]),this.state.year);
                const snapshot={...this.state};
                const raw=await this.loader.load(snapshot.group,snapshot.family,snapshot.frequency,snapshot.year);
                if(revision!==this.revision)return;
                const previous=await this.loader.load(snapshot.group,snapshot.family,snapshot.frequency,String(Number(snapshot.year)-1));
                if(revision!==this.revision)return;
                this.rows=canonical(raw,this.state);this.previous=previous;
                this.syncFilters(changed);this.render();this.notice.textContent='';
            } catch(error) {if(revision===this.revision)this.notice.textContent='No se pudo actualizar la selección: '+error.message+'. Se conserva la última vista válida.';}
            finally {if(revision===this.revision)this.container.setAttribute('aria-busy','false');}
        }
        syncFilters(changed) {
            const s=this.state,c=this.controls;
            const months=[...new Set(this.rows.map(r=>r.observation_date.slice(5,7)))].sort();
            if(!months.includes(s.month) || ['family','group','year','frequency'].includes(changed))s.month=months.at(-1);
            setOptions(c.month,months.map(m=>[m,MONTHS[Number(m)-1]]),s.month);c.month.parentElement.hidden=s.frequency!=='monthly';
            const provinces=[...new Set(this.rows.filter(r=>r.entity_type==='province').map(r=>r.geography))].sort();
            if(!provinces.includes(s.province))s.province='Argentina';
            setOptions(c.province,[['Argentina','Total nacional'],...provinces.map(p=>[p,p])],s.province);c.province.parentElement.hidden=!provinces.length;
            const categories=this.rows.filter(r=>['category','category_rollup'].includes(r.entity_type) && !isTotal(r));
            const methods=[...new Set(categories.map(r=>r.methodology))];
            if(!methods.includes(s.method))s.method=methods.at(-1) || '';
            setOptions(c.method,methods.map(m=>[m,METHODS[m] || m]),s.method);c.method.parentElement.hidden=methods.length<2;
            const names=[...new Set(categories.filter(r=>r.methodology===s.method).map(r=>r.category))].sort();
            if(s.category!=='TOTAL' && !names.includes(s.category))s.category='TOTAL';
            // The source has no cached national mean: start with an explicitly selected published category.
            if(changed==='family' && s.family==='carcass_weight' && s.group==='production')s.category=names.includes('Novillito')?'Novillito':names[0] || 'TOTAL';
            setOptions(c.category,[['TOTAL','Total publicado'],...names.map(n=>[n,n])],s.category);c.category.parentElement.hidden=!names.length;c.category.disabled=s.province!=='Argentina';
            const ages=[...new Set(categories.filter(r=>r.methodology===s.method && r.category===s.category).map(r=>r.age_class))].filter(Boolean).sort();
            if(!ages.includes(s.age))s.age=ages.find(a=>dentition(a)===dentition(s.age)) || ages[0] || '';
            setOptions(c.age,ages.map(a=>[a,a]),s.age);c.age.parentElement.hidden=!ages.length;c.age.disabled=s.province!=='Argentina';
            const species=[...new Set(this.rows.map(r=>r.species))];setOptions(c.species,species.map(v=>[v,v==='bovinos_y_bubalinos'?'Bovinos y bubalinos (no separables)':'Bovinos']));
            c.method.disabled=s.province!=='Argentina';
            for(const key of ['category','age','method'])if(c[key].disabled)c[key].parentElement.hidden=true;
            this.contextSummary.textContent='Más filtros';this.contextSummary.title=[s.province==='Argentina'?'Total nacional':s.province,s.category==='TOTAL'?'Total publicado':s.category,s.age].filter(Boolean).join(' · ');
            this.contextFilters.hidden=!['province','category','age','method'].some(key=>!c[key].parentElement.hidden);
        }
        render() {
            const s=this.state,series=selectedSeries(this.rows,s).sort((a,b)=>a.observation_date.localeCompare(b.observation_date));
            const anchor=point(series,s);this.series=series;this.anchor=anchor;
            const entry=this.loader.descriptors(s.group,s.family,s.frequency,s.year)[0].entry;
            this.renderMetadata(entry,series);
            const provisional=series.some(r=>r.flags?.some(f=>f.includes('provisional')));
            const dimension=s.category!=='TOTAL'?`${s.category}${s.age?' · '+s.age:''} · ámbito nacional`:s.province==='Argentina'?'Total nacional':s.province;
            const missingMean=s.family==='carcass_weight' && s.category==='TOTAL' && series.every(r=>number(r.value)===null);
            this.methodNote.textContent=[dimension,provisional?'Dato provisorio':'Observaciones publicadas',
                s.group==='sspm' && s.family==='production'?'Base de peso no identificada: no se atribuye RCH.':'',
                s.province!=='Argentina'?'Categoría/dentición no aplican a la tabla provincial.':'',
                s.year==='2019'?'Clasificaciones de 2019 separadas; sin empalme.':'',
                series.some(r=>r.species==='bovinos_y_bubalinos')?'Bovinos y bubalinos publicados conjuntamente; no separables.':'',
                missingMean?'Media total sin resultado publicado/cacheado; seleccioná una categoría.':'',
                s.frequency==='year_to_date'?(anchor?.period_end.slice(5,7)!=='12'?'Acumulado parcial publicado; no es un año completo.':'Acumulado publicado enero–diciembre; frecuencia diferenciada del anual.'):''].filter(Boolean).join(' · ');
            this.selectionNote.textContent=[dimension,provisional?'Dato provisorio':'Observaciones publicadas',missingMean?'Media total sin resultado publicado: seleccioná una categoría.':'',series.some(r=>r.species==='bovinos_y_bubalinos')?'Bovinos y bubalinos no separables':'',s.group==='sspm' && s.family==='production'?'Base de peso no identificada':'',s.frequency==='year_to_date' && (anchor || series[0])?caption(anchor || series[0]):''].filter(Boolean).join(' · ');
            this.kpis[0].heading.textContent=s.family==='slaughter'?'Cabezas publicadas':s.family==='production'?'Toneladas publicadas':'Peso medio publicado';
            this.kpis[0].value.textContent=anchor?format(number(anchor.value)):'Seleccioná una serie';this.kpis[0].note.textContent=anchor?`${caption(anchor)} · ${unit(anchor)}`:'';
            const variation=yearAgo(anchor,this.previous);this.kpis[1].value.textContent=variation===null?'Sin base comparable':format(variation)+' %';this.kpis[1].note.textContent='Mismo período, unidad y metodología';
            const pool=[...series,...selectedSeries(this.previous,s)];const ytd=derivedYTD(pool,anchor),rolling=rollingReference(pool,anchor),territory=territorialDistribution(this.rows,anchor);
            const currentComposition=compositionDistribution(this.rows,s,anchor),previousAnchor=point(selectedSeries(this.previous,s),s);
            const previousComposition=compositionDistribution(this.previous,s,previousAnchor),compositionChange=compareComposition(currentComposition,previousComposition);
            this.analyticsResult={ytd,rolling,territory,currentComposition,compositionChange};
            this.analyticsMethod.textContent=s.family==='carcass_weight'?'El peso es una media publicada: nunca se suman ni promedian categorías para reconstruir el total. Una media móvil temporal exige 12 meses completos de la misma categoría y publicación.':
                'El acumulado calculado suma meses completos de enero al cierre seleccionado; su interanual usa el mismo cierre. Se mantiene separado del acumulado publicado. Media móvil: promedio simple de 12 meses consecutivos. Participaciones: valor dividido por total nacional publicado del mismo período. Cambio de composición: diferencia de participaciones, en puntos porcentuales, respecto del mismo mes del año anterior.';
            this.analyticsMethod.textContent+=' Las denticiones se comparan sin diferencias de mayúsculas ni espacios; las etiquetas originales permanecen en el detalle. Las referencias no cruzan publicaciones, unidades ni clasificaciones.';
            this.kpis[2].heading.textContent='Acumulado calculado · mismo cierre';this.kpis[2].node.hidden=!ytd;this.kpis[2].value.textContent=ytd?format(ytd.value):'';
            this.kpis[2].note.textContent=ytd?`Enero–${MONTHS[ytd.count-1]} · ${unit(anchor)} · ${ytd.variation===null?'Sin base interanual comparable':format(ytd.variation)+' % i.a.'}`:'';
            const components=classificationRows(this.rows,s,anchor);
            const chosenProvince=territory?.items.find(i=>i.row.geography===s.province),chosenCategory=currentComposition?.items.find(i=>sameSeries(i.row,anchor));
            const concentration=s.province!=='Argentina'?chosenProvince?.share:s.category!=='TOTAL'?chosenCategory?.share:territory?.top3;
            this.kpis[3].node.hidden=concentration===null || concentration===undefined;this.kpis[3].heading.textContent=s.province!=='Argentina'?'Participación provincial':s.category!=='TOTAL'?'Participación de la categoría':'Concentración · Top 3 provincias';
            this.kpis[3].value.textContent=format(concentration)+' %';this.kpis[3].note.textContent=s.province!=='Argentina'?s.province:s.category!=='TOTAL'?label(anchor):territory?.items.slice(0,3).map(i=>i.row.geography).join(' · ') || '';
            const moving=series.map(r=>rollingReference(pool,r)?.mean ?? null);const overlays=moving.some(v=>v!==null)?[{label:'Media móvil 12 meses',data:moving,borderColor:'#b7c1ce',backgroundColor:'transparent',borderDash:[6,4],pointRadius:0,spanGaps:false}]:[];
            this.draw(this.timeline,'line',series.map(r=>caption(r)),series,`Evolución · ${dimension}`,unit(anchor || series[0]),false,{datasets:overlays});
            this.timeline.desc.textContent='Año seleccionado · el mes determina los KPIs y desgloses. Sin interpolar faltantes.';
            const provinces=anchor?this.rows.filter(r=>r.entity_type==='province' && r.observation_date===anchor.observation_date && r.period_end===anchor.period_end):[];
            this.ranking.node.hidden=s.family!=='slaughter' || !provinces.length || s.category!=='TOTAL';
            if(!this.ranking.node.hidden)this.renderRanking(provinces,territory,anchor);
            this.composition.node.hidden=s.family==='production' || !components.length || s.province!=='Argentina';
            if(!this.composition.node.hidden){
                const shares=currentComposition?.items.map(i=>i.share);const prior=compositions=>compositions?.map(i=>i.previous);
                this.draw(this.composition,'bar',components.map(label),components,s.family==='carcass_weight'?'Peso publicado por categoría / dentición':'Composición nacional por categoría / dentición',shares?'% del total publicado':unit(components[0]),true,
                    {values:shares,datasets:compositionChange?[{label:'Mismo mes del año anterior',data:prior(compositionChange),backgroundColor:'#b7c1ce77',borderColor:'#b7c1ce',borderWidth:1,_observations:compositionChange.map(i=>i.previousRow)}]:[],
                        tooltip:(_,i)=>compositionChange?[`Cambio: ${format(compositionChange[i].pp)} puntos porcentuales`]:[]});
                this.composition.desc.textContent=(METHODS[s.method] || '')+' · '+caption(anchor)+(shares?(compositionChange?' · Participaciones actual y mismo mes del año anterior':' · Participación actual; sin base comparable para cambio'):' · Valores publicados; sin sumar promedios ni inferir participaciones');
            }
            const facts=[];
            if(rolling)facts.push(`Respecto de la media móvil de 12 meses: ${format(rolling.difference)} ${unit(anchor)}${rolling.percent===null?'':' ('+format(rolling.percent)+' %)'}`);
            if(territory?.items.length && s.province==='Argentina' && s.category==='TOTAL')facts.push(`Mayor participación territorial: ${territory.items[0].row.geography}, ${format(territory.items[0].share)} %`);
            if(currentComposition){const leading=[...currentComposition.items].sort((a,b)=>b.share-a.share)[0];facts.push(`Categoría principal: ${label(leading.row)}, ${format(leading.share)} %`);}
            if(compositionChange){const change=[...compositionChange].sort((a,b)=>Math.abs(b.pp)-Math.abs(a.pp))[0];facts.push(`Mayor cambio de composición: ${label(change.row)}, ${format(change.pp)} p.p. respecto del mismo mes del año anterior`);}
            this.highlightList.replaceChildren(...facts.map(f=>element('li','',f)));this.highlights.hidden=!facts.length;
            this.analyticNote.textContent=s.frequency==='monthly' && !rolling?'Media móvil omitida: se requieren 12 observaciones mensuales consecutivas de la misma serie.':'';
            const priorYears=[...new Set(this.loader.descriptors(s.group,s.family,'monthly').map(d=>Number(d.file.year)))].filter(y=>y<Number(s.year) && y>=Number(s.year)-5);
            this.referenceSection.hidden=s.frequency!=='monthly' || !usable(anchor) || priorYears.length<3;
            if(this.referenceSection.hidden)this.referenceSection.open=false;
            this.referenceStatus.textContent='Abrí esta sección para cargar hasta cinco años previos de la misma publicación.';this.seasonality.node.hidden=true;this.heatmap.replaceChildren();
            this.referenceResult=null;this.referenceRows=[];
            if(this.referenceSection.open)this.loadReferences();
            this.syncSecondary();
            this.fillTable(this.table,series);
            for(const [key,button] of this.familyButtons)button.setAttribute('aria-pressed',String(key===s.family));
        }
        syncSecondary() {
            this.breakdown.hidden=this.ranking.node.hidden;
        }
        renderRanking(provinces,distribution,anchor) {
            this.charts.get(this.ranking.canvas)?.destroy();this.charts.delete(this.ranking.canvas);
            const key=anchor.observation_id;if(this.rankKey!==key){this.rankKey=key;this.rankExpanded=false;}
            const items=distribution?.items || [...provinces].filter(r=>number(r.value)!==null).sort((a,b)=>number(b.value)-number(a.value)).map((row,i)=>({row,rank:i+1,share:null}));
            this.ranking.heading.textContent='Ranking provincial · '+caption(anchor);this.ranking.desc.textContent=`${this.rankExpanded?items.length:Math.min(6,items.length)} de ${items.length} provincias · cabezas${distribution?' y participación sobre total nacional publicado':' · sin participación comparable'}`;
            const list=element('div','carnes-ranked-bars');list.setAttribute('role','list');
            for(const item of items.slice(0,this.rankExpanded?items.length:6)){
                const node=element('div','carnes-ranked-item');node.setAttribute('role','listitem');const button=element('button','carnes-rank-detail');button.type='button';button.onclick=()=>this.openDetail(item.row);
                button.append(element('span','',`${item.rank}. ${item.row.geography}`),element('span','',`${format(number(item.row.value))}${item.share===null?'':' · '+format(item.share)+' %'}`));
                const track=element('div','carnes-rank-track');const bar=element('div');bar.style.width=(number(items[0]?.row.value)>0?number(item.row.value)/number(items[0].row.value)*100:0)+'%';track.append(bar);node.append(button,track);list.append(node);
            }
            const toggle=element('button','carnes-detail-button',this.rankExpanded?'Ver primeras 6':'Ver todas las provincias');toggle.type='button';toggle.hidden=items.length<=6;toggle.setAttribute('aria-expanded',String(this.rankExpanded));toggle.onclick=()=>{this.rankExpanded=!this.rankExpanded;this.renderRanking(provinces,distribution,anchor);this.ranking.body.querySelector('.carnes-detail-button')?.focus();};
            this.ranking.body.hidden=false;this.ranking.empty.hidden=true;this.ranking.body.replaceChildren(list,toggle);
        }
        async loadReferences() {
            const revision=this.revision,s={...this.state},anchor=this.anchor;const request=++this.referenceRevision;
            this.referenceStatus.textContent='Cargando referencias de la misma publicación…';this.seasonality.node.hidden=true;this.heatmap.replaceChildren();
            try {
                const years=Array.from({length:6},(_,i)=>String(Number(s.year)-i));const raw=await Promise.all(years.map(year=>this.loader.load(s.group,s.family,'monthly',year)));
                if(revision!==this.revision || request!==this.referenceRevision || !this.referenceSection.open)return;
                const rows=raw.flatMap(r=>selectedSeries(r,s));const reference=historicalReference(rows,anchor);this.referenceResult=reference;this.referenceRows=rows;
                const parts=[];
                if(reference?.range){const r=reference.range,v=number(anchor.value);parts.push(`Rango de 36 meses anteriores (${caption(r.rows[0])}–${caption(r.rows.at(-1))}): ${format(r.min)}–${format(r.max)} ${unit(anchor)}. Dato seleccionado ${v<r.min?'por debajo':v>r.max?'por encima':'dentro'} del rango observado. Sin ajuste estacional; no es una banda estadística.`);}
                else parts.push('Sin 36 meses consecutivos comparables para el rango reciente.');
                if(reference?.seasonality){this.seasonality.node.hidden=false;const yearRows=MONTHS.map((_,i)=>rows.find(r=>sameSeries(r,anchor) && r.observation_date.slice(0,7)===`${s.year}-${String(i+1).padStart(2,'0')}`) || {...anchor,observation_date:`${s.year}-${String(i+1).padStart(2,'0')}-01`,value:'',value_status:'missing'});
                    this.draw(this.seasonality,'line',MONTHS,yearRows,'Estacionalidad · año seleccionado y patrón previo',unit(anchor),false,{datasets:[{label:'Media mensual histórica',data:reference.seasonality.map(m=>m.mean),borderColor:'#b7c1ce',borderDash:[6,4],pointRadius:0,backgroundColor:'transparent'}],tooltip:(_,i)=>[`Rango histórico del mes: ${format(reference.seasonality[i].min)}–${format(reference.seasonality[i].max)} ${unit(anchor)}`]});
                    this.seasonality.desc.textContent=`${s.year} frente a ${reference.years.map(y=>y.year).join(', ')} · años previos completos (${reference.years.length}); media aritmética por mes. No implica causalidad ni prueba de anomalía.`;
                    this.renderHeatmap(rows,anchor,[...reference.years.map(y=>y.year),Number(s.year)]);
                }else parts.push(`Estacionalidad y matriz omitidas: se requieren al menos 3 años previos completos y homogéneos (${reference?.years.length || 0} disponibles).`);
                if(rows.some(r=>r.species!==anchor.species))parts.push('Se excluyen las observaciones con distinta cobertura de especies.');
                this.referenceStatus.textContent=parts.join(' ');
            }catch(error){if(revision===this.revision && request===this.referenceRevision)this.referenceStatus.textContent='Referencias no disponibles: '+error.message+'. La selección principal se conserva.';}
        }
        renderHeatmap(rows,anchor,years) {
            this.heatmap.replaceChildren(element('h3','chart-title','Año × mes · niveles publicados'));
            const cells=years.flatMap(year=>MONTHS.map((_,m)=>{const found=rows.filter(r=>sameSeries(r,anchor) && r.observation_date.slice(0,7)===`${year}-${String(m+1).padStart(2,'0')}`);return {year,month:m,row:found.length===1 && usable(found[0])?found[0]:null};}));
            const values=cells.filter(c=>c.row).map(c=>number(c.row.value)),min=Math.min(...values),max=Math.max(...values);
            this.heatmap.append(element('p','chart-desc',`${unit(anchor)} · escala de menor (${format(min)}) a mayor (${format(max)}). Sin dato se distingue de cero. Usá flechas para recorrer los meses.`));
            const wrap=element('div','carnes-heatmap-scroll'),grid=element('div','carnes-heatmap-grid');grid.setAttribute('role','group');grid.setAttribute('aria-label','Valores mensuales de la misma serie');grid.append(element('span','','Año'),...MONTHS.map(m=>element('span','',m.slice(0,3))));
            const readout=element('p','carnes-heatmap-readout','Seleccioná o enfocá un mes para ver período, valor y fuente.');readout.setAttribute('role','status');const buttons=[];
            for(const [index,cell] of cells.entries()){
                if(cell.month===0)grid.append(element('strong','',String(cell.year)));
                const text=`${MONTHS[cell.month]} ${cell.year}: ${cell.row?format(number(cell.row.value))+' '+unit(cell.row)+' · '+cell.row.source:'Sin observación comparable'}`;
                const button=element('button','carnes-heatmap-cell',cell.row?'':'—');button.type='button';button.tabIndex=index===0?0:-1;button.title=text;button.setAttribute('aria-label',text);
                if(cell.row){const intensity=max>min?(number(cell.row.value)-min)/(max-min):.5;button.style.backgroundColor=`rgba(104,194,158,${.15+.8*intensity})`;}
                button.onfocus=()=>{buttons.forEach(b=>b.tabIndex=b===button?0:-1);readout.textContent=text;};button.onmouseenter=()=>readout.textContent=text;button.onclick=()=>{readout.textContent=text;if(cell.row)this.openDetail(cell.row);};
                button.onkeydown=event=>{const move={ArrowRight:1,ArrowLeft:-1,ArrowDown:12,ArrowUp:-12};if(move[event.key]!==undefined){event.preventDefault();buttons[Math.max(0,Math.min(cells.length-1,index+move[event.key]))].focus();}};buttons.push(button);grid.append(button);
            }wrap.append(grid);this.heatmap.append(wrap,readout);
        }
        renderMetadata(entry,series) {
            const info=sourceState(entry,this.loader.states);
            this.badge.textContent=STATUS_LABELS[info.status] || 'Estado no informado';this.badge.dataset.status=info.status;
            this.badge.className='source-update-status__badge carnes-state carnes-state--'+(info.status==='PIPELINE_ERROR'?'error':info.status==='UPDATED'?'success':['SOURCE_UNAVAILABLE','NO_PUBLICATION'].includes(info.status)?'warning':'neutral');
            const descriptors=this.loader.descriptors(this.state.group,this.state.family,this.state.frequency);
            const years=descriptors.map(d=>d.file.year).sort();const observed=series.filter(r=>number(r.value)!==null);
            const last=observed.at(-1);const timestamp=new Date(entry.last_successful_capture);
            const capture=Number.isFinite(timestamp.valueOf())?new Intl.DateTimeFormat('es-AR',{dateStyle:'short',timeStyle:'short',timeZone:'UTC'}).format(timestamp)+' UTC':'No informada';
            this.familyTitle.textContent=FAMILIES[this.state.family];this.metaText.replaceChildren();
            for(const [title,value] of [['Fuente',entry.source],['Último dato de la selección',last?caption(last):'Sin valor publicado'],['Unidad',unit(last || series[0])],['Cobertura de archivos',`${years[0]}–${years.at(-1)}`]]){const item=element('span');item.append(element('span','carnes-meta-label',title),element('strong','',value));this.metaText.append(item);}
            this.sourceLink.title='Captura: '+capture;this.metadata.dataset.capture=capture;
            if(info.historical && info.status!=='HISTORICAL_ENDED')this.metaText.append(element('span','','Serie histórica finalizada'));
            if(this.loader.statusUnavailable)this.metaText.append(element('span','','Metadata de estado no disponible'));
            this.sourceLink.href=entry.source_url;
        }
        draw(card,type,labels,rows,title,unitLabel,horizontal=false,extra={}) {
            this.charts.get(card.canvas)?.destroy();this.charts.delete(card.canvas);card.heading.textContent=title;card.canvas.setAttribute('aria-label',title+' · '+unitLabel);
            const observed=rows.some(r=>number(r.value)!==null);card.body.hidden=!observed;card.empty.hidden=observed;card.empty.textContent='Sin valores publicados para esta selección.';
            if(!observed || !root.Chart)return;
            const tickIndexes=new Set(labels.length<=6?labels.map((_,i)=>i):Array.from({length:6},(_,i)=>Math.round(i*(labels.length-1)/5)));
            const chart=new root.Chart(card.canvas,{type,data:{labels,datasets:[{label:unitLabel,data:extra.values || rows.map(r=>number(r.value)),borderColor:'#68c29e',backgroundColor:type==='line'?'#68c29e33':'#77a9d7bb',pointRadius:3,tension:0,spanGaps:false},...(extra.datasets || [])]},
                options:{responsive:true,maintainAspectRatio:false,indexAxis:horizontal?'y':'x',animation:false,plugins:{legend:{display:!!extra.datasets?.length,labels:{color:'#b7c1ce',boxWidth:18}},datalabels:{display:false},tooltip:{backgroundColor:'#101a27',titleColor:'#eef3f7',bodyColor:'#eef3f7',padding:12,callbacks:{label:context=>{
                    const r=rows[context.dataIndex];if(context.datasetIndex>0){const original=context.dataset._observations?.[context.dataIndex];return [`${context.dataset.label}: ${format(number(context.raw))} ${unitLabel}`,...(original?[caption(original),'Fuente: '+original.source]:[])];}
                    return [...(extra.values?[`${format(extra.values[context.dataIndex])} ${unitLabel}`]:[]),`${format(number(r.value))} ${unit(r)}`,caption(r),`Fuente: ${r.source}`,r.category==='Total general'?'Total publicado':label(r),...(extra.tooltip?.(r,context.dataIndex) || [])];}}}},
                    scales:{x:{title:{display:true,text:unitLabel,color:'#b2c0cd'},ticks:{color:'#b2c0cd',maxRotation:0,...(!horizontal?{autoSkip:false,callback:value=>tickIndexes.has(Number(value))?labels[Number(value)]:''}:{maxTicksLimit:6})},grid:{display:false},beginAtZero:horizontal},y:{ticks:{color:'#b2c0cd',autoSkip:false},grid:{color:'#2e435855'},beginAtZero:type==='bar'}}}});
            this.charts.set(card.canvas,chart);
        }
        makeTable(parent,title) {
            const section=element('div','chart-card carnes-records');section.append(element('h3','chart-title',title));
            const count=element('p','chart-desc');section.append(count);
            const searchLabel=element('label','filter-label','Buscar observaciones');const search=element('input','filter-select carnes-search');search.type='search';search.id='carnes-search-'+(this.tableSequence=(this.tableSequence || 0)+1);searchLabel.htmlFor=search.id;section.append(searchLabel,search);
            const exportButton=element('button','filter-select carnes-export','Descargar selección CSV');exportButton.type='button';section.append(exportButton);
            const wrap=element('div','carnes-table-wrap');const table=element('table','carnes-table');table.append(element('caption','carnes-table-caption',title+' · fuente, período y captura disponibles en Ver detalle'));const head=element('thead');const tr=element('tr');
            for(const name of ['Período','Ámbito / categoría','Valor','Unidad','Condición','Detalle']){const th=element('th','',name);th.scope='col';tr.append(th);}head.append(tr);const body=element('tbody');table.append(head,body);wrap.append(table);wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',title+' · tabla desplazable');section.append(wrap);
            const pagination=element('div','carnes-pagination');const back=element('button','carnes-detail-button','Anterior'),more=element('button','carnes-detail-button','Siguiente');back.type='button';more.type='button';pagination.append(back,more);section.append(pagination);parent.append(section);
            const result={body,more,back,search,exportButton,count,page:0,term:''};search.oninput=()=>{result.page=0;result.term=search.value;this.fillTable(result,result.rows || []);};return result;
        }
        fillTable(table,rows) {
            if(table.rows!==rows){table.page=0;table.rows=rows;}
            const normalized=value=>String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('es');
            const found=rows.filter(r=>normalized([caption(r),r.geography,label(r),r.source,unit(r),r.value,format(number(r.value)),r.flags?.some(f=>f.includes('provisional'))?'Provisorio':'Publicado'].join(' ')).includes(normalized(table.term)));
            table.page=Math.max(0,Math.min(table.page,Math.ceil(found.length/10)-1));
            table.body.replaceChildren();
            for(const row of found.slice(table.page*10,table.page*10+10)) {
                const tr=element('tr');for(const text of [caption(row),row.geography+(isTotal(row)?' · Total publicado':' · '+label(row)),format(number(row.value)),unit(row),row.flags?.some(f=>f.includes('provisional'))?'Provisorio':'Publicado'])tr.append(element('td','',text));
                const cell=element('td');const button=element('button','carnes-detail-button','Ver detalle');button.type='button';button.setAttribute('aria-label','Ver detalle · '+caption(row)+' · '+row.geography);button.onclick=()=>this.openDetail(row);cell.append(button);tr.append(cell);table.body.append(tr);
            }
            if(!found.length){const tr=element('tr');const cell=element('td','','Sin observaciones para la búsqueda');cell.colSpan=6;tr.append(cell);table.body.append(tr);}
            table.count.textContent=`${found.length?table.page*10+1:0}–${Math.min(found.length,(table.page+1)*10)} de ${found.length} resultados · ${rows.length} observaciones en la selección. La descarga incluye toda la selección.`;
            table.more.disabled=(table.page+1)*10>=found.length;table.back.disabled=table.page===0;table.more.onclick=()=>{table.page++;this.fillTable(table,rows);};table.back.onclick=()=>{table.page--;this.fillTable(table,rows);};
            table.exportButton.onclick=()=>{const esc=v=>'"'+String(v ?? '').replaceAll('"','""')+'"';const csv=[FIELDS.join(','),...rows.map(r=>FIELDS.map(k=>esc(r[k])).join(','))].join('\n');const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=element('a');a.href=url;a.download='carnes-seleccion.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
        }
        buildDetail(parent) {
            this.detail=element('dialog','carnes-detail');this.detail.setAttribute('aria-labelledby','carnes-detail-title');
            const close=element('button','carnes-detail-button','Cerrar detalle');close.type='button';close.onclick=()=>this.detail.close();
            const title=element('h3','chart-title','Detalle de observación');title.id='carnes-detail-title';this.detailContent=element('div');this.detail.append(close,title,this.detailContent);parent.append(this.detail);
            this.detail.addEventListener('click',event=>{if(event.target===this.detail){const bounds=this.detail.getBoundingClientRect();if(event.clientX<bounds.left || event.clientX>bounds.right || event.clientY<bounds.top || event.clientY>bounds.bottom)this.detail.close();}});
        }
        openDetail(row) {
            this.detailContent.replaceChildren();const list=element('dl','carnes-detail-list');
            for(const [title,value] of [['Fuente',row.source],['Observación',caption(row)],['Valor',format(number(row.value))],['Unidad',unit(row)],['Categoría',row.category],['Dentición',row.age_class || 'No aplica'],['Geografía',row.geography],['Especie',row.species==='bovinos_y_bubalinos'?'Bovinos y bubalinos (no separables)':'Bovinos'],['Condición',row.flags?.some(f=>f.includes('provisional'))?'Provisorio':'Publicado'],['Captura',row.capture_date]])list.append(element('dt','',title),element('dd','',value));
            const link=element('a','','Ver fuente institucional');link.href=row.source_url;link.target='_blank';link.rel='noopener noreferrer';
            const technical=element('details','carnes-technical');technical.append(element('summary','','Detalles de trazabilidad'));const fields=element('dl','carnes-detail-list');
            for(const key of FIELDS)fields.append(element('dt','',key),element('dd','',row[key] || '—'));technical.append(fields);this.detailContent.append(list,link,technical);this.detail.showModal();
        }
        buildHistory() {
            const p=this.historyContainer;const filters=element('div','filters-grid');p.append(filters);
            const family=select(filters,'carnes-history-family','Serie histórica',[['livestock_price','Precios Liniers · finalizada'],['exports','Exportaciones · finalizada']]);
            const year=select(filters,'carnes-history-year','Año',[]);const metric=select(filters,'carnes-history-metric','Magnitud / moneda',[]);
            const meta=element('p','carnes-metadata');p.append(meta);const chart=chartCard(p,'Serie histórica finalizada');const table=this.makeTable(p,'Observaciones históricas seleccionadas');let revision=0;
            const update=async(changed)=>{
                const current=++revision;
                const years=[...new Set(this.loader.descriptors('archive',family.value,'monthly').map(d=>d.file.year))].sort().reverse();
                setOptions(year,years.map(y=>[y,y]),changed==='family'?years[0]:year.value);
                const metrics=family.value==='livestock_price'?[['novillo_price_ARS','Novillo · ARS/kg vivo'],['novillo_price_USD','Novillo · USD/kg vivo']]:
                    [['export_volume_rch','Volumen · toneladas equivalentes RCH'],['export_value','Valor · miles USD'],['export_unit_value_rch','Valor unitario · USD/tonelada equivalente RCH']];
                setOptions(metric,metrics,metric.value);
                try {const rows=await this.loader.load('archive',family.value,'monthly',year.value);if(current!==revision)return;
                    const selected=rows.filter(r=>r.metric===metric.value);const entry=this.loader.entries('archive')[0];const state=sourceState(entry,this.loader.states);
                    meta.textContent=`Serie histórica finalizada · ${entry.source} · Cobertura: ${date(entry.first_observation)}–${date(entry.last_observation)} · Último dato: ${MONTHS[Number(entry.last_observation.slice(5,7))-1]} ${entry.last_observation.slice(0,4)} · Captura: ${entry.last_successful_capture} · ${unit(selected[0])}`+
                        (state.status!=='HISTORICAL_ENDED'?' · Estado: '+(STATUS_LABELS[state.status] || 'Estado no informado'):'');
                    this.draw(chart,'line',selected.map(caption),selected,metrics.find(([key])=>key===metric.value)[1]+' · Serie histórica finalizada',unit(selected[0]));this.fillTable(table,selected);
                }catch(error){if(current===revision)meta.textContent='No se pudo cargar la serie histórica: '+error.message;}
            };
            family.onchange=()=>update('family');year.onchange=()=>update('year');metric.onchange=()=>update('metric');update('family');
        }
    }
    const api={Loader,View,Analytics,parseCSV,validateRows,canonical,selectedSeries,reconcile,yearAgo,point,sourceState,classificationRows,provincialShare,caption,number,FIELDS,
        mount(container){if(!container._carnesView){container._carnesView=new View(container);return container._carnesView.mount();}return Promise.resolve();}};
    if(typeof module!=='undefined' && module.exports)module.exports=api;else root.Carnes=api;
})(typeof globalThis!=='undefined'?globalThis:this);
