# Manifests de derechos de datos

Esta carpeta contiene manifests de ejemplo que declaran la procedencia y los derechos de
uso de un dataset. Ningún dataset entra en persistencia sin que su manifest supere la
validación de `decide_persistent_use`.

## Esquema

- `docs/data/source-manifest.schema.json` define la estructura canónica.

## Ejemplos

- `devsoul-synthetic.example.json`: dataset sintético propiedad de DevSoul. Autorizado
  para persistencia (`ALLOW`).
- `unapproved-external.example.json`: contenido externo (Deriv) sin autorización escrita.
  Rechazado por el gate (`DENY`).

Los `manifest_hash` son SHA-256 canónicos calculados sobre los campos del manifest
(excluyendo el propio hash). El dominio `devsoul_quant.domain.data_rights` los recalcula y
verifica de forma determinista.

## Reglas

- Los manifests no contienen credenciales, DSNs, emails ni rutas locales absolutas.
- Un manifest Deriv solo puede reclamar retención persistente si incluye una referencia de
  autorización escrita (`written_authorization_ref`).
