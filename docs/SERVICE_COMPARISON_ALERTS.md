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
