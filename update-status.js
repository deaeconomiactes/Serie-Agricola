/* Presentation only: explicit pipeline status, never calendar-based freshness. */
(function (root) {
    'use strict';
    const states = {
        UPDATED: ['Actualizado', 'success'],
        NO_OP_ALREADY_CURRENT: ['Actualizado', 'success'],
        NO_PUBLICATION: ['Sin nueva publicación', 'warning'],
        SOURCE_UNAVAILABLE: ['Último dato válido', 'warning'],
        MAGYP_LAST_VALID: ['Último dato válido', 'warning'],
        LAST_VALID: ['Último dato válido', 'warning'],
        PIPELINE_ERROR: ['Error de actualización', 'error'],
        STATIC: ['Fuente estática', 'neutral']
    };
    function dateLabel(value) {
        if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'No informada';
        const d = new Date(value + 'T00:00:00Z');
        if (!Number.isFinite(d.valueOf()) || d.toISOString().slice(0, 10) !== value) return 'No informada';
        return value.split('-').reverse().join('/');
    }
    function timestampLabel(value) {
        if (typeof value !== 'string' || !Number.isFinite(Date.parse(value))) return 'No informada';
        // Legacy SIO metadata has no timezone: preserve its clock instead of inventing UTC.
        if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(value))
            return dateLabel(value.slice(0,10)) + ' ' + value.slice(11,16) + ' (hora de origen)';
        return new Intl.DateTimeFormat('es-AR', {timeZone:'America/Argentina/Buenos_Aires',
            day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit', hourCycle:'h23'})
            .format(new Date(value)).replace(',', '');
    }
    function describe(metadata = {}, summary = {}, options = {}) {
        metadata = metadata || {};
        const status = metadata.status ?? metadata.result ?? metadata.source_status;
        if (!states[status] && !options.showUnknown) return null;
        const [label, tone] = states[status] || ['Estado no informado', 'neutral'];
        const day = dateLabel(metadata.last_valid_date ?? metadata.last_observation_date ?? summary.date_max);
        const updated = timestampLabel(metadata.last_successful_update ?? summary.updated_at);
        let details = status === 'UPDATED' || status === 'NO_OP_ALREADY_CURRENT'
            ? `Último dato: ${day}` : status === 'NO_PUBLICATION'
            ? `Último dato disponible: ${day}` : status === 'PIPELINE_ERROR'
            ? 'Se conserva la última versión válida'
            : `Fuente temporalmente no disponible · Última actualización exitosa: ${updated}`;
        if (options.showDates) {
            const explanation = status === 'PIPELINE_ERROR' ? 'Se conserva la última versión válida · ' :
                ['SOURCE_UNAVAILABLE', 'LAST_VALID', 'MAGYP_LAST_VALID'].includes(status) ? 'Fuente temporalmente no disponible · ' : '';
            details = `${explanation}Último dato: ${day} · Actualización exitosa: ${updated}`;
            if (status === 'STATIC') details = `Último dato: ${day} · Actualización exitosa: ${updated} · Actualización manual; sin automatización`;
        }
        return {status, label, tone, details,
            sourceLabel: options.sourceLabel || 'MCBA',
            title: `${options.sourceLabel || 'MCBA'} · Estado publicado por ${options.stateOrigin || 'el proceso de actualización'} · Fecha solicitada: ${dateLabel(metadata.requested_date)}`};
    }
    function render(node, metadata, summary, visible = true, options = {}) {
        if (!node) return;
        const view = visible ? describe(metadata, summary, options) : null;
        node.hidden = !view;
        node.replaceChildren();
        if (!view) return;
        node.className = 'source-update-status source-update-status--' + view.tone;
        node.title = view.title;
        const badge = node.ownerDocument.createElement('span');
        badge.className = 'source-update-status__badge';
        badge.textContent = view.sourceLabel + ' · ' + view.label;
        const detail = node.ownerDocument.createElement('span');
        detail.textContent = view.details;
        node.append(badge, detail);
    }
    async function loadFreshness() {
        try {
            const response = await fetch('data/magyp/reports/PRICE_FRESHNESS_STATUS.json', {cache:'no-store'});
            if (!response.ok) return {};
            const report = await response.json();
            if (report.schema_version !== 'price-freshness-v1' || !Array.isArray(report.sources)) return {};
            return Object.fromEntries(report.sources.filter(row => row && typeof row.source_family === 'string' &&
                (states[row.status] || row.status === 'NOT_REPORTED')).map(row => [row.source_family, row]));
        } catch (_) { return {}; }
    }
    const api = {describe, render, loadFreshness};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.SourceUpdateStatus = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
