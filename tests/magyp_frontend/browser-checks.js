// Run via agent-browser eval --stdin on the local dashboard after data loads.
window.mcbaIntegrationChecks = [];
window.recordMCBACheck = function (name, condition, detail) {
    const entry = {
        name, passed: Boolean(condition), detail,
        filters:getPriceFilters(), frequency:priceFrequency,
        rows:filteredPriceData.length, sources:[...new Set(filteredPriceData.map(r=>r.source_status))],
        observation_levels:[...new Set(filteredPriceData.map(r=>r.observation_level))],
        kpi:document.getElementById('priceKpiAverage').textContent,
        semaphore_rows:document.querySelectorAll('#priceTrafficLightBody tr').length
    };
    window.mcbaIntegrationChecks.push(entry);
    return entry;
};
