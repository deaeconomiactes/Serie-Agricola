/* Independent official meat-sector observations. No acquisition or inferred totals. */
(function (root) {
    'use strict';
    const BASE = 'data/carnes/dashboard/';
    const VERSION = 'carnes-v1';
    const FAMILIES = {slaughter:'Faena bovina', production:'Producción bovina', carcass_weight:'Peso medio'};
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
            return !isTotal(row) && row.category===state.category && row.methodology===state.method && (!state.age || row.age_class===state.age);
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
        if(!row || number(row.value)===null)return null;
        const year=Number(row.observation_date.slice(0,4))-1;
        const matches=previous.filter(other=>COMPARABLE.every(key=>other[key]===row[key]) && other.observation_date===year+row.observation_date.slice(4) &&
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
        constructor(container,loader=new Loader()) {this.container=container;this.loader=loader;this.revision=0;this.charts=new Map();
            this.state={family:'slaughter',group:'detail',frequency:'monthly',year:'',month:'',province:'Argentina',category:'TOTAL',age:'',method:'resolution_32_2018_dentition'};}
        async mount() {
            this.container.replaceChildren();this.notice=element('p','carnes-notice','Cargando datos oficiales…');this.notice.setAttribute('role','status');this.container.append(this.notice);
            try {await this.loader.init();this.build();await this.update('family');}
            catch(error){this.notice.textContent='No se pudo cargar Carnes: '+error.message;const retry=element('button','filter-select','Reintentar');retry.type='button';retry.onclick=()=>this.mount();this.container.append(retry);}
        }
        build() {
            const c=this.container;
            this.metadata=element('div','carnes-metadata');this.badge=element('span','source-update-status__badge');this.metaText=element('span');this.sourceLink=element('a','','Ver fuente');this.sourceLink.target='_blank';this.sourceLink.rel='noopener noreferrer';this.metadata.append(this.badge,this.metaText,this.sourceLink);c.append(this.metadata);
            const filters=element('div','price-filters filters-card filters-grid carnes-filters');filters.setAttribute('aria-label','Filtros de Carnes');c.append(filters);this.controls={};
            for(const [key,title] of [['family','Familia'],['group','Fuente'],['frequency','Frecuencia'],['year','Año'],['month','Mes'],['province','Provincia'],['category','Categoría'],['age','Dentición'],['method','Clasificación'],['species','Especie']]) {
                const input=select(filters,'carnes-'+key,title,[]);this.controls[key]=input;
                if(key!=='species')input.addEventListener('change',()=>{this.state[key]=input.value;reconcile(this.state,key);this.update(key);});
            }
            this.controls.species.disabled=true;this.methodNote=element('p','method-note carnes-method');c.append(this.methodNote);
            const kpis=element('div','kpi-grid carnes-kpis');c.append(kpis);this.kpis=[card(kpis,'Cabezas'),card(kpis,'Variación interanual'),card(kpis,'Participación provincial'),card(kpis,'Categoría / dentición principal')];
            this.timeline=chartCard(c,'Evolución temporal');const breakdown=element('div','carnes-breakdown');c.append(breakdown);this.ranking=chartCard(breakdown,'Ranking provincial');this.composition=chartCard(breakdown,'Composición nacional por categoría / dentición');
            this.table=this.makeTable(c,'Observaciones de la serie · año seleccionado');
            const details=element('details','chart-card carnes-history');const summary=element('summary','','Series históricas finalizadas');details.append(summary);
            const history=element('div','carnes-history-content');details.append(history);c.append(details);
            history.append(element('p','chart-desc','Liniers 1998–2019 y exportaciones 1998–2019 · Series históricas finalizadas. No representan indicadores corrientes.'));
            this.historyContainer=history;details.addEventListener('toggle',()=>{if(details.open && !this.historyBuilt){this.historyBuilt=true;this.buildHistory();}});
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
            if(!ages.includes(s.age))s.age=ages[0] || '';
            setOptions(c.age,ages.map(a=>[a,a]),s.age);c.age.parentElement.hidden=!ages.length;c.age.disabled=s.province!=='Argentina';
            const species=[...new Set(this.rows.map(r=>r.species))];setOptions(c.species,species.map(v=>[v,v==='bovinos_y_bubalinos'?'Bovinos y bubalinos (no separables)':'Bovinos']));
            c.method.disabled=s.province!=='Argentina';
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
            this.kpis[0].heading.textContent=s.family==='slaughter'?'Cabezas publicadas':s.family==='production'?'Toneladas publicadas':'Peso medio publicado';
            this.kpis[0].value.textContent=anchor?format(number(anchor.value)):'Seleccioná una serie';this.kpis[0].note.textContent=anchor?`${caption(anchor)} · ${unit(anchor)}`:'';
            const variation=yearAgo(anchor,this.previous);this.kpis[1].value.textContent=variation===null?'Sin base comparable':format(variation)+' %';this.kpis[1].note.textContent='Mismo período, unidad y metodología';
            const share=provincialShare(anchor,this.rows);this.kpis[2].node.hidden=s.family!=='slaughter' || s.group!=='detail' || s.category!=='TOTAL';this.kpis[2].value.textContent=share===null?(s.province==='Argentina'?'Seleccioná una provincia':'Sin base comparable'):format(share)+' %';this.kpis[2].note.textContent='Sobre el total nacional publicado (categorías en mensual)';
            const components=classificationRows(this.rows,s,anchor);
            const complete=components.length && components.every(r=>number(r.value)!==null) && components.some(r=>number(r.value)>0);
            const largest=complete?[...components].sort((a,b)=>number(b.value)-number(a.value))[0]:null;
            this.kpis[3].node.hidden=s.family!=='slaughter' || s.group!=='detail' || s.province!=='Argentina';this.kpis[3].value.textContent=largest?label(largest):'Sin base comparable';
            this.kpis[3].note.textContent='Clasificación seleccionada · sin sumar tablas';
            this.draw(this.timeline,'line',series.map(r=>caption(r)),series,`Evolución · ${dimension}`,unit(anchor || series[0]));
            this.timeline.desc.textContent='Año seleccionado · el mes determina los KPIs y desgloses. Sin interpolar faltantes.';
            const provinces=anchor?this.rows.filter(r=>r.entity_type==='province' && r.observation_date===anchor.observation_date && r.period_end===anchor.period_end):[];
            this.ranking.node.hidden=s.family!=='slaughter' || !provinces.length || s.category!=='TOTAL';
            const ranked=provinces.filter(r=>number(r.value)!==null).sort((a,b)=>number(b.value)-number(a.value));
            if(!this.ranking.node.hidden){this.draw(this.ranking,'bar',ranked.map(r=>r.geography),ranked,'Ranking provincial · '+caption(anchor),'cabezas',true);this.ranking.desc.textContent='Distribución nacional del período; no suma totales de otras tablas.';}
            this.composition.node.hidden=s.family==='production' || !components.length || s.province!=='Argentina';
            if(!this.composition.node.hidden){this.draw(this.composition,'bar',components.map(label),components,
                s.family==='carcass_weight'?'Peso publicado por categoría / dentición':'Composición nacional por categoría / dentición',unit(components[0]),true);this.composition.desc.textContent=(METHODS[s.method] || '')+' · '+caption(anchor);}
            this.fillTable(this.table,series);
        }
        renderMetadata(entry,series) {
            const info=sourceState(entry,this.loader.states);const labels={UPDATED:'Actualizado',HISTORICAL_ENDED:'Serie histórica finalizada',SOURCE_UNAVAILABLE:'Último dato válido · fuente no disponible',NO_PUBLICATION:'Sin nueva publicación',PIPELINE_ERROR:'Error de actualización',NOT_REPORTED:'Estado no informado'};
            this.badge.textContent=labels[info.status] || 'Estado no informado';this.badge.dataset.status=info.status;
            this.badge.className='source-update-status__badge carnes-state carnes-state--'+(info.status==='PIPELINE_ERROR'?'error':info.status==='UPDATED'?'success':['SOURCE_UNAVAILABLE','NO_PUBLICATION'].includes(info.status)?'warning':'neutral');
            const descriptors=this.loader.descriptors(this.state.group,this.state.family,this.state.frequency);
            const years=descriptors.map(d=>d.file.year).sort();const observed=series.filter(r=>number(r.value)!==null);
            const last=observed.at(-1);const timestamp=new Date(entry.last_successful_capture);
            const capture=Number.isFinite(timestamp.valueOf())?new Intl.DateTimeFormat('es-AR',{dateStyle:'short',timeStyle:'short',timeZone:'UTC'}).format(timestamp)+' UTC':'No informada';
            this.metaText.textContent=`${entry.source} · Cobertura de archivos: ${years[0]}–${years.at(-1)} · Último dato de la selección: ${last?date(last.period_end):'Sin valor publicado'} · Captura: ${capture} · ${unit(last || series[0])}`+
                (info.historical && info.status!=='HISTORICAL_ENDED'?' · Serie histórica finalizada':'')+(this.loader.statusUnavailable?' · Metadata de estado no disponible':'');
            this.sourceLink.href=entry.source_url;
        }
        draw(card,type,labels,rows,title,unitLabel,horizontal=false) {
            this.charts.get(card.canvas)?.destroy();this.charts.delete(card.canvas);card.heading.textContent=title;card.canvas.setAttribute('aria-label',title+' · '+unitLabel);
            const observed=rows.some(r=>number(r.value)!==null);card.body.hidden=!observed;card.empty.hidden=observed;card.empty.textContent='Sin valores publicados para esta selección.';
            if(!observed || !root.Chart)return;
            const chart=new root.Chart(card.canvas,{type,data:{labels,datasets:[{label:unitLabel,data:rows.map(r=>number(r.value)),borderColor:'#68c29e',backgroundColor:type==='line'?'#68c29e33':'#77a9d7bb',pointRadius:3,tension:0,spanGaps:false}]},
                options:{responsive:true,maintainAspectRatio:false,indexAxis:horizontal?'y':'x',animation:false,plugins:{legend:{display:false},datalabels:{display:false},tooltip:{callbacks:{label:context=>{
                    const r=rows[context.dataIndex];return [`${format(number(r.value))} ${unit(r)}`,caption(r),`Fuente: ${r.source}`,r.category==='Total general'?'Total publicado':label(r)];}}}},
                    scales:{x:{ticks:{color:'#b2c0cd',maxRotation:0},grid:{color:'#2e435855'},beginAtZero:horizontal},y:{ticks:{color:'#b2c0cd',autoSkip:false},grid:{color:'#2e435855'},beginAtZero:type==='bar'}}}});
            this.charts.set(card.canvas,chart);
        }
        makeTable(parent,title) {
            const section=element('div','chart-card carnes-records');section.append(element('h3','chart-title',title));
            const exportButton=element('button','filter-select carnes-export','Descargar selección CSV');exportButton.type='button';section.append(exportButton);
            const wrap=element('div','carnes-table-wrap');const table=element('table','carnes-table');const head=element('thead');const tr=element('tr');
            for(const name of ['Período','Ámbito / categoría','Valor','Unidad','Condición','Fuente / trazabilidad'])tr.append(element('th','',name));head.append(tr);const body=element('tbody');table.append(head,body);wrap.append(table);section.append(wrap);
            const more=element('button','filter-select carnes-export','Mostrar más');more.type='button';section.append(more);parent.append(section);
            return {body,more,exportButton,limit:40};
        }
        fillTable(table,rows) {
            table.body.replaceChildren();
            for(const row of rows.slice(0,table.limit)) {
                const tr=element('tr');for(const text of [caption(row),row.geography+(isTotal(row)?' · Total publicado':' · '+label(row)),format(number(row.value)),unit(row),row.flags?.some(f=>f.includes('provisional'))?'Provisorio':'Publicado'])tr.append(element('td','',text));
                const cell=element('td');const link=element('a','',row.source);link.href=row.source_url;link.target='_blank';link.rel='noopener noreferrer';const details=element('details');details.append(element('summary','','Ver detalle'));
                details.append(element('p','',`Origen: ${row.source_locator} · Captura: ${row.capture_date} · RAW SHA-256: ${row.raw_sha256} · Flags: ${row.quality_flags}`));cell.append(link,details);tr.append(cell);table.body.append(tr);
            }
            if(!rows.length){const tr=element('tr');const cell=element('td','','Sin observaciones');cell.colSpan=6;tr.append(cell);table.body.append(tr);}
            table.more.hidden=rows.length<=table.limit;table.more.onclick=()=>{table.limit+=40;this.fillTable(table,rows);};
            table.exportButton.onclick=()=>{const esc=v=>'"'+String(v ?? '').replaceAll('"','""')+'"';const csv=[FIELDS.join(','),...rows.map(r=>FIELDS.map(k=>esc(r[k])).join(','))].join('\n');const url=URL.createObjectURL(new Blob(['\ufeff'+csv],{type:'text/csv;charset=utf-8'}));const a=element('a');a.href=url;a.download='carnes-seleccion.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
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
                        (state.status!=='HISTORICAL_ENDED'?' · Estado: '+state.status:'');
                    this.draw(chart,'line',selected.map(caption),selected,metrics.find(([key])=>key===metric.value)[1]+' · Serie histórica finalizada',unit(selected[0]));this.fillTable(table,selected);
                }catch(error){if(current===revision)meta.textContent='No se pudo cargar la serie histórica: '+error.message;}
            };
            family.onchange=()=>update('family');year.onchange=()=>update('year');metric.onchange=()=>update('metric');update('family');
        }
    }
    const api={Loader,View,parseCSV,validateRows,canonical,selectedSeries,reconcile,yearAgo,point,sourceState,classificationRows,provincialShare,caption,number,FIELDS,
        mount(container){if(!container._carnesView){container._carnesView=new View(container);return container._carnesView.mount();}return Promise.resolve();}};
    if(typeof module!=='undefined' && module.exports)module.exports=api;else root.Carnes=api;
})(typeof globalThis!=='undefined'?globalThis:this);
