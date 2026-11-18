# Service comparison alerts / Összehasonlító riasztások

## Magyar

Új csoport: service-comparison-security. Mappa: AI Job Portal. A meglévő 12 szabály mellé 3 új szabály kerül, összesen 15. A küszöbök kezdeti példák, a valós forgalom alapján finomítandók.

| Szabály neve | Feltétel | Kivárás |
| --- | --- | --- |
| MatchWise \| Render backend \| High CPU usage | A Render saját CPU-keretének több mint 80%-a | 5 perc |
| MatchWise \| Render backend \| HTTP 5xx burst | Legalább 5 naplózott, nem health 5xx válasz az előző 5 percben | 2 perc |
| MatchWise \| Render backend \| Rejected login burst | Legalább 10 POST /auth/login vagy /api/auth/login kérés 401 válasszal az előző 5 percben | 2 perc |

A szabályok percenként értékelődnek. A kivárás alatt minden értékeléskor fenn kell álljon a feltétel. A csúszó ötperces ablakban a hibák akkor is benne maradnak egy ideig, ha már megszűntek. A küldést a meglévő Telegram-szabályozás is késleltetheti (30 másodperces kezdeti várakozás, meglévő csoportnál 5 perces csoportfrissítés).

A CPU-szabály friss forrásadatot (5 percen belül), friss gyűjtési kísérletet (4 percen belül), sikeres gyűjtést és működő, hibamentes Node Exportert igényel. A naplóalapú szabályok a naplócollector friss sikerét (5 percen belül), a textfile hibamentességét, valamint Loki/Alloy sikeres health mérését igénylik. Ezek a health mérések nem bizonyítják, hogy minden napló megérkezett. Az üres Loki számláló 0 csak érvényes monitoringfeltételek mellett használható.

Hiányzó adatok és lekérdezési hiba esetén az új szabályok KeepLast állapotot használnak. A korábbi riasztási állapot megmarad; a hiányzó adat nem jelent igazolt helyreállást. Az új szabályok nem helyettesítik a meglévő monitoringhiba-riasztásokat. A Render erőforrásgyűjtésének hibáját egyelőre a dashboard adathiánya mutatja, külön új collector-riasztás nem készült.

A sok 401 vagy 5xx vizsgálandó jelenség, nem bizonyított támadás. Valós rendszerterhelés vagy tömeges bejelentkezési kísérlet helyett először csak a lekérdezéseket ellenőrizzük.

## English

New group: service-comparison-security. Folder: AI Job Portal. Three rules are added to the existing twelve, giving fifteen rules. Thresholds are starting examples and should be adjusted to real traffic.

- High CPU usage: over 80% of the Render CPU limit for 5 minutes.
- HTTP 5xx burst: at least 5 logged non-health 5xx responses in the last 5 minutes, with a 2-minute pending period.
- Rejected login burst: at least 10 POST /auth/login or /api/auth/login requests returning 401 in the last 5 minutes, with a 2-minute pending period.

Rules run every minute. The condition must remain true during the pending period. Old errors stay in the rolling five-minute window until they expire. Telegram routing adds a 30-second initial wait or up to the five-minute group update interval for an existing notification group.

CPU requires a successful collection, a source sample under five minutes old, an attempt under four minutes old and a healthy Node Exporter/textfile reader. Log rules require a successful log collector run within five minutes, no textfile errors, and successful Loki/Alloy health checks. These checks do not prove complete log delivery. Empty Loki counts become zero only when the monitoring gate has valid data.

All new rules use KeepLast on missing data or query errors. The previous state is retained; missing data does not prove recovery. Existing monitoring-failure rules still apply. Resource collection failure is currently visible as gaps in the dashboard; this change does not add a separate resource collector alert.

Many 401 or 5xx responses are a reason to investigate, not proof of an attack.

## Read-only preflight / Csak olvasó ellenőrzés

This checks actual PromQL and LogQL queries. It does not install rules, send notifications or generate application traffic. Expected values: A=0 under normal load and D=1 for the two log rules. Nonzero A can be a real threshold breach. Empty data is a reason to investigate before installing.

A program nem telepít szabályt, nem küld értesítést, és nem generál alkalmazásforgalmat. Normál helyzetben az A érték 0, a naplószabályok D értéke 1. Az A=1 valódi küszöbátlépést is jelenthet. Üres adat esetén telepítés előtt keresd meg az okot.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
git show FETCH_HEAD:grafana/provisioning/alerting/service-comparison-alerts.json > /tmp/matchwise-service-comparison-alerts.json
git show FETCH_HEAD:scripts/check-service-comparison-queries.py > /tmp/matchwise-check-service-comparison-queries.py
python3 /tmp/matchwise-check-service-comparison-queries.py /tmp/matchwise-service-comparison-alerts.json
```

Installation comes after a successful query preflight. Grafana provisioning and expression evaluation, pending/recovery and Telegram delivery require separate live checks. The existing policy sends category=security alerts to AI Job Telegram. Notification testing must be coordinated with the team.

Telepítés a sikeres lekérdezéspróba után következik. A Grafana-szabálybetöltést, az összetett kifejezéseket, kivárást/helyreállást és a Telegram-küldést külön kell élesben ellenőrizni. A meglévő értesítési házirend a security kategóriát is az AI Job Telegram csatornára irányítja.

## Validation status / Ellenőrzési állapot

New JSON structure, unique UIDs, query references and thresholds checked locally. Full original promtool suite was not run in this environment (promtool and PyYAML unavailable). The updated validator checks all 15 rules structurally and retains the original 12-rule PromQL scenario suite. The read-only preflight is required for the new datasource queries; it does not validate Grafana expression execution.

A helyi szerkezeti ellenőrzés sikeres. A teljes régi promtool teszt itt nem futott le, mert a szükséges eszközök hiányoznak. A három új szabály éles lekérdezéspróbája és Grafana-értékelése még hátravan.

Sources: [Grafana file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/), [KeepLast behavior](https://grafana.com/docs/grafana/latest/alerting/fundamentals/alert-rule-evaluation/nodata-and-error-states/).

## Successful preflight and installation / Sikeres próba és telepítés

2026-11-18 operator output: CPU A=0, 5xx A=0 and D=1, login A=0 and D=1. All five datasource queries succeeded with nonempty, unlabelled vectors. No threshold was breached. This validates actual PromQL/LogQL syntax and current monitoring gates. It does not yet validate Grafana expressions B/E/F/C or notification delivery.

A felhasználó kimenete alapján mind az öt éles lekérdezés sikeres. A riasztási feltételek 0 értékűek, a monitoringfeltételek 1 értékűek. A Grafana-kifejezések és a Telegram-küldés még nincsenek ellenőrizve.

Install only the new provisioning file, then restart the existing Grafana container to load alert resources. Grafana is briefly unavailable during restart; metric and log collectors continue running. Rules become active and use the existing Telegram policy if a condition is met.

Csak az új szabályfájlt telepítsd, majd indítsd újra a meglévő Grafana konténert. A Grafana rövid ideig nem lesz elérhető. A szabályok aktívvá válnak, és feltételteljesülés esetén a meglévő Telegram-értesítést használják.

```bash
cd ~/ai-job-monitoring
python3 -m json.tool /tmp/matchwise-service-comparison-alerts.json > /dev/null
install -m 644 /tmp/matchwise-service-comparison-alerts.json grafana/provisioning/alerting/service-comparison-alerts.json
sudo docker restart monitoring-grafana
```

Run commands in order and stop on errors. Open Alerting -> Alert rules -> AI Job Portal -> service-comparison-security. After one or two evaluation cycles, expect three rules with state Normal and health OK. Initial datasource values do not guarantee the same values later. Record state and health separately; Normal with Error health is not a passing check. An empty group or evaluation errors require investigation before testing alerts.

Sorrendben futtasd a parancsokat, hiba esetén állj meg. A Grafanában az új csoportban 1–2 értékelési ciklus után három szabályt várunk Normal állapottal és OK health értékkel. A kezdeti értékek később változhatnak. A Normal állapot önmagában nem elég, a health is legyen OK.

Next: verify Grafana provisioning and expressions, then perform a controlled alert test without generating real backend load or login attacks. Viewer access and notification tests remain pending. The new file is initially untracked in the live main checkout; move it outside the checkout before a later branch switch if Git reports an overwrite conflict.

Következő lépés: Grafana-betöltés és kifejezések ellenőrzése, majd kontrollált riasztási teszt. Viewer hozzáférés és értesítés még nincs igazolva. Az új fájl az éles main checkoutban kezdetben nem verziókövetett; későbbi ágváltáskor Git-ütközés esetén előbb helyezd a repón kívülre.

To temporarily disable only these rules, set isPaused=true on all three rules in the installed JSON file, validate JSON, and restart Grafana. Removing the file alone may leave provisioned rules in Grafana; it is not a reliable rollback.

Csak az új szabályok ideiglenes leállításához az isPaused mezőt állítsd true értékre mindhárom szabálynál a telepített JSON fájlban, ellenőrizd a JSON-t, majd indítsd újra a Grafanát. A fájl törlése önmagában nem megbízható visszaállítás, mert a szabályok bent maradhatnak.

## Startup incident / Indulási hiba

Operator reported Grafana restarting after the new rules were installed. Container status confirms a restart loop; startup logs are still needed to establish the exact cause. Inspection found invalid annotations in all three new rules: __dashboardUid__ was set without __panelId__. Grafana requires both together. Removed the incomplete optional links and added a validator assertion. The data queries and thresholds are unchanged. JSON and annotation-pair checks passed; live startup recovery is pending.

A Grafana az új szabályok telepítése után újraindulási ciklusba került. Az új fájlban hibás, hiányos dashboard/panel hivatkozást találtunk. Eltávolítottuk a hiányos hivatkozást, és az ellenőrzőt kiegészítettük. A pontos indulási hiba naplóval, a helyreállítás éles próbával még ellenőrizendő.

Emergency recovery: preserve the last 80 container log lines, move only service-comparison-alerts.json outside the provisioning directory, restart monitoring-grafana and check /api/health. Do not delete volumes or change other rules. Removing this file avoids loading the invalid definitions at startup; it does not guarantee deletion of any already-persisted rules. Install the corrected version only after confirming startup.

Gyors helyreállítás: mentsd/nézd meg az utolsó 80 naplósort, helyezd csak az új service-comparison-alerts.json fájlt a provisioning könyvtáron kívülre, indítsd újra a Grafanát, majd ellenőrizd az /api/health választ. A javított fájlt a működés visszaállítása után telepítsd.

Reference: https://grafana.com/docs/grafana/latest/alerting/alerting-rules/link-alert-rules-to-panels/
