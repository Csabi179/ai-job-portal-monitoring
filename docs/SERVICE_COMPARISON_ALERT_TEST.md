# Controlled alert test / Kontrollált riasztási teszt

## Magyar

A teszt három külön szabályt készít TEST előtaggal, a service-comparison-test csoportban. Az eredeti 15 szabályt nem módosítja. A bemeneti értékek helyett időzített Prometheus tesztjelet és állandó 1-es monitoringfeltételt használ. A Grafana reduce/math/threshold kifejezései, a valódi 5 és 2 perces kivárások és az értesítési útvonal megmaradnak.

Ez a Grafana állapotváltásait és a Telegram-értesítést ellenőrzi. Nem bizonyítja a valódi CPU/napló küszöbök vagy a monitoringkapu helyes működését. A valódi adatforrás-lekérdezések korábbi éles próbája sikeres. Nem készül hamis alkalmazásnapló vagy erőforrásmérés; a backend nem kap tesztforgalmat.

A teszt a meglévő csapat Telegram-csoportjába küld TEST jelölésű üzeneteket. A category=security_test külön értesítési csoportot képez a meglévő házirendben. A csatorna ugyanaz, a csoportosítás eltér a valódi security kategóriától.

A tesztjel a generálás után 2 perccel válik 1-gyé, 12 percig marad 1, utána 0 lesz. A generátor kiírja a kezdő és befejező UTC-időt. Telepítsd rögtön generálás után; ha több percet vársz, generáld újra, különben kimaradhat a teljes kivárás bemutatása. Az Oracle órájának helyesnek kell lennie.

## English

The helper creates three separate TEST rules in service-comparison-test. It does not modify the original fifteen rules. It replaces datasource inputs with a timed Prometheus test signal and a constant healthy monitoring gate. It keeps Grafana reduce/math/threshold expressions, the real 5-minute and 2-minute pending periods and the existing notification path.

This tests Grafana state transitions and Telegram delivery. It does not prove real CPU/log thresholds or the real monitoring gate. The real datasource queries passed an earlier live check. No fake application logs or resource measurements are created and no traffic is sent to the backend.

TEST notifications go to the existing team Telegram group. category=security_test creates a separate notification group under the existing policy. The contact point is the same, but grouping differs from real security alerts.

The signal turns on two minutes after generation, stays on for twelve minutes, then turns off automatically. The helper prints start/end times in UTC. Install immediately after generation; regenerate if installation is delayed by several minutes. The Oracle clock must be correct.

## Generate and install / Elkészítés és telepítés

The original rule source is downloaded to /tmp; the helper writes only the temporary fixture. Stop on command errors. No credentials are required by the helper. Restarting Grafana briefly interrupts its UI.

A program csak az ideiglenes tesztfájlt készíti el. Hiba esetén állj meg. Nem kell kulcsot vagy jelszót megadni. A Grafana újraindításakor rövid ideig nem lesz elérhető.

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
git show FETCH_HEAD:scripts/service-comparison-alert-test.py > /tmp/matchwise-service-comparison-alert-test.py
git show FETCH_HEAD:grafana/provisioning/alerting/service-comparison-alerts.json > /tmp/matchwise-alert-test-source.json

python3 /tmp/matchwise-service-comparison-alert-test.py generate --source /tmp/matchwise-alert-test-source.json --output /tmp/matchwise-service-comparison-test.json

python3 -m json.tool /tmp/matchwise-service-comparison-test.json > /dev/null
install -m 644 /tmp/matchwise-service-comparison-test.json grafana/provisioning/alerting/service-comparison-test.json
sudo docker restart monitoring-grafana
```

After startup / Indulás után:

```bash
curl -fsS http://127.0.0.1:3000/api/health
```

Open Alerting -> Alert rules -> AI Job Portal -> service-comparison-test.

| Since generation / Generálástól | Expected / Várt eredmény |
| --- | --- |
| 0–2 minutes / perc | Normal, health OK |
| About 2–3 minutes / perc | Pending after next evaluation / Pending a következő értékeléskor |
| About 4–5 minutes / perc | 5xx and login tests Firing / 5xx és login teszt Firing |
| About 7–8 minutes / perc | CPU test Firing / CPU teszt Firing |
| About 14–15 minutes / perc | All return to Normal / Mind visszatér Normal állapotba |

These are estimates based on one-minute evaluation. Telegram adds a 30-second group wait and five-minute group updates; several rules may share one message. Resolved notifications can take up to a group update after recovery. A short pending period may not appear in a screenshot unless you refresh.

Az időpontok becslések, a percenkénti értékeléstől függenek. A Telegram kezdetben 30 másodpercet vár, később 5 perces csoportfrissítést használ. Több szabály egy üzenetben is érkezhet. A resolved üzenet a helyreállás után a következő csoportfrissítésig várhat.

Do not clean up immediately on Firing: first observe both firing and resolved notifications. Missing Telegram messages must be investigated; health OK alone does not prove delivery. Record screenshots, message times, health and state. Do not share bot tokens.

Firing után még ne töröld a tesztet: először várd meg a resolved értesítést is. Az OK health önmagában nem igazolja a Telegram-küldést. Rögzítsd az állapotokat és az üzenetek időpontját.

## Cleanup / Eltávolítás

After observing recovery and resolved delivery, replace the fixture with an explicit deletion file using the same installed path and restart Grafana. This removes only mw_test_cpu_flow, mw_test_5xx_flow and mw_test_login_flow. Do not delete the fixture file before Grafana has processed these deleteRules; simply removing a provisioning file may leave rules in its database. Keep the deletion file until cleanup is verified.

A helyreállás és a resolved értesítés ellenőrzése után ugyanazon a telepített útvonalon törlési fájlra cseréljük a tesztet. Csak a három tesztszabályt törli. Az egyszerű fájltörlés nem elég: a szabályok az adatbázisban megmaradhatnak. A törlési fájlt az ellenőrzésig hagyd a helyén.

```bash
cd ~/ai-job-monitoring
python3 /tmp/matchwise-service-comparison-alert-test.py cleanup --output /tmp/matchwise-service-comparison-test.json
install -m 644 /tmp/matchwise-service-comparison-test.json grafana/provisioning/alerting/service-comparison-test.json
sudo docker restart monitoring-grafana
```

Verify that the three TEST rules are gone and the original 15 rules remain. The empty test group/folder may remain visible. The deletion file can remain; it is idempotent. If later switching the repository branch, move untracked deployed files outside the checkout if Git reports a conflict.

Ellenőrizd, hogy a három TEST szabály eltűnt, az eredeti 15 megmaradt. Az üres tesztcsoport látszódhat. A törlési fájl ismételt betöltése nem hozza vissza a szabályokat.

Emergency: to end the test early, use the same cleanup command. Early deletion may prevent observing the normal recovery/resolved path, so it is not a successful full-cycle test.

Megszakításhoz ugyanazt az eltávolító parancsot használd. A korai törlés nem igazolja a normál helyreállási folyamatot.

## Validation / Ellenőrzés

Three local unittest methods passed: source immutability and preserved expression graphs/pending periods; deletion limited to test IDs; invalid source rejection and atomic output replacement. Live Grafana state transitions and Telegram delivery remain pending until operator evidence arrives. Local tests do not exercise Grafana itself.

Három helyi teszt sikeres. Az éles Grafana-állapotváltás és a Telegram-küldés csak a felhasználó visszajelzése után tekinthető igazoltnak.

Source: [Grafana alert file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/).

## Live evidence 2026-11-18 / Éles bizonyíték

Operator supplied Grafana /api/health with database=ok and screenshots showing all three production rules present, all three TEST rules present, and Telegram firing followed by resolved notifications for HTTP 5xx burst, High CPU usage and Rejected login burst. This confirms notification delivery and recovery messages through the real Grafana/Telegram path for all three synthetic tests. The Grafana screenshot shows an intermediate test state; it does not independently confirm final state/health fields. Cleanup is pending operator execution and confirmation.

A felhasználó kimenete és képei alapján a Grafana működik, az eredeti három szabály és a három tesztszabály betöltődött. Mindhárom tesztszabályhoz megérkezett a firing és a resolved Telegram-üzenet. A szintetikus teszt értesítési és helyreállási köre igazolt. Ez nem valódi backendhiba, túlterhelés vagy sikertelen bejelentkezési hullám próbája. A tesztszabályok eltávolítása még hátravan.
