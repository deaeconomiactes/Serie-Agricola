"""Public observations for independent meat-sector economic families."""
import hashlib
import json

VERSION = 'carnes-v1'
FAMILIES = {'livestock_price', 'slaughter', 'production', 'carcass_weight', 'live_weight', 'exports', 'meat_price'}
FIELDS = ['observation_id','record_id','source_id','source','source_url','family','metric','species',
    'observation_date','period_end','frequency','category','category_raw','age_class','geography','geography_raw',
    'geography_level','market','table_id','entity_type','entity_id','entity_name','entity_tax_id','entity_activity','currency','unit','unit_raw',
    'weight_basis','value','value_raw','value_status','methodology','quality_flags','source_locator',
    'capture_date','capture_id','raw_sha256','schema_version']


class DataError(ValueError):
    pass


def digest(value):
    if not isinstance(value, bytes):
        value=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(value).hexdigest()


def observation(**values):
    """Parser contract; capture/provenance and deterministic IDs are attached by runner.

    Required: family, metric, species, observation_date (ISO period start), frequency
    (monthly/annual), category, geography, geography_level, unit, value (decimal string
    or None), value_raw (original published string/number), source_locator.
    Preserve originals in category_raw/geography_raw/unit_raw. No conversions implied.
    quality_flags is a list[str]; methodology distinguishes incompatible classifications.
    Entity-level rows retain type/id/name, rollups use explicit entity_type='total'.
    """
    row={key:'' for key in FIELDS}
    row.update(currency='NOT_APPLICABLE',weight_basis='NOT_IDENTIFIED',schema_version=VERSION,
        value_status='missing' if values.get('value') is None else 'observed',quality_flags=[])
    row.update(values)
    if row['family'] not in FAMILIES:raise DataError('Unknown economic family')
    for raw,normal in [('category_raw','category'),('geography_raw','geography'),('unit_raw','unit')]:
        if not row[raw]:row[raw]=row[normal]
    return row
