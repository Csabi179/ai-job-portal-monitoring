# Repeatable monitoring tests / Újrafuttatható monitoringtesztek

Updated / Frissítve: 2026-11-18. Feature branch: feat/service-comparison. Main merge is intentionally deferred / Main összevonás később.

## Magyar

A tesztprogramok és leírások verziózottak. A /tmp példányok csak futtatási másolatok: későbbi próbához töltsd le újra a kívánt Git-verziót, ne számíts a /tmp tartalmának megmaradására.

| Teszt | Program | Hatás és leírás |
|---|---|---|
| Valódi 404-riasztás | [test-backend-404-once.py](../../scripts/test-backend-404-once.py) | Legfeljebb 20 egymás utáni kérés a rögzített backend egy nem létező tesztútvonalára. Valódi napló és riasztás. [Leírás](../SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md) |
| Három tesztriasztás állapotmenete | [service-comparison-alert-test.py](../../scripts/service-comparison-alert-test.py) | Külön TEST szabályok, időzített szintetikus értékek, valódi Telegram-küldés. [Telepítés és explicit törlés](../SERVICE_COMPARISON_ALERT_TEST.md) |
| Lekérdezés-ellenőrzés | [check-service-comparison-queries.py](../../scripts/check-service-comparison-queries.py) | Csak olvasás a helyi Prometheus/Loki felől; nem generál backendforgalmat. [Előkészítés](../SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md) |
| Konfiguráció és PromQL-esetek | [validate-alerting.py](../../scripts/validate-alerting.py) | 16 állandó szabály szerkezete és 12 eredeti szabály 38 PromQL-esete; PyYAML és megfelelő promtool kell. Nem küld értesítést. |
| Eredeti 12 szabály kézi próbái | [alert-rule-test-helper.py](alert-rule-test-helper.py) | Helyi HTTP-fixture és átmeneti Prometheus-konfiguráció; állapotmentés/visszaállítás. [Magyar](../alert-rule-tests.md), [English](../alert-rule-tests.en.md) |
| Python helyi ellenőrzések | [collector](../../scripts/test_render_metrics.py), [query checker](../../scripts/test_security_query_checks.py), [synthetic helper](../../scripts/test_service_comparison_alert_test.py) | Automatizált tesztek; nem helyettesítik az Oracle/Grafana/Telegram próbát. |

A valódi login-riasztást az üzemeltető tíz szándékosan hibás bejelentkezéssel már kipróbálta. Ehhez jelenleg nincs külön hitelesítőadatot kezelő automatikus program. A 403/429 panelekhez és a forgalomösszehasonlításhoz nincs külön riasztás vagy támadásszimulátor.

### Valódi 404-próba később

Az Oracle gépen, egyszer futtatva:

```bash
cd ~/ai-job-monitoring
git fetch origin feat/service-comparison
MW_TEST_REF=$(git rev-parse FETCH_HEAD)
printf 'Test source: %s\n' "$MW_TEST_REF"
git show "$MW_TEST_REF":scripts/test-backend-404-once.py > /tmp/matchwise-test-backend-404-once.py
python3 /tmp/matchwise-test-backend-404-once.py
```

A program váratlan státusznál, hálózati hibánál vagy túl hosszú futásnál megáll. Nem követ átirányítást, nem használ jelszót, nem indít párhuzamos kéréseket és nem próbálkozik újra automatikusan. Húsz 404 után várd meg a valódi HTTP 404 burst szabályt és a Telegram firing/resolved üzeneteit. Újabb futás előtt hagyd kifutni az előző eseményeket az ötperces ablakból és ellenőrizd a helyreállást; a háttérforgalom is beleszámít.

A szintetikus háromszabályos teszthez a külön runbookban szereplő generate/install/cleanup lépések kellenek. A tesztfájl egyszerű törlése nem elég; a Grafana adatbázisában maradt TEST szabályokat deleteRules-szal kell eltávolítani.

Minden új próbánál rögzítsd: dátum/időzóna, fenti Git-azonosító, cél, eredmény, szabályállapot/health, firing/resolved és végső helyreállás. Titkos értékeket és valódi alkalmazásnaplókat ne másolj Gitbe. [Tesztnapló](../monitoring-tests.md).

### Ez DDoS?

A mostani 404-próba kis mennyiségű, engedélyezett, funkcionális riasztásteszt: egy gépről, legfeljebb húsz egymás utáni kéréssel, nem az erőforrások kimerítésére készült. A riasztás bekapcsolása önmagában nem jelent DDoS-t.

A DoS a szolgáltatás elérhetőségének megzavarását célozza; a DDoS ennek több gépről/forrásból végzett formája. A kérések száma önmagában nem dönti el a besorolást. Ez a teszt nem igazolja a rendszer túlterhelés- vagy DDoS-állóságát.

## English

All listed helpers and guides are versioned. Files under /tmp are temporary execution copies; fetch the desired Git version again for later tests. The table links to the real 404 check, timed TEST-rule generator, read-only query checker, configuration/PromQL validator and original manual fixture helper.

The real 404 script sends at most twenty sequential requests to one fixed backend's intentionally nonexistent test path. It stops on unexpected status, network failure or excessive duration. It does not follow redirects, use credentials, send concurrent requests or retry automatically. Wait for the five-minute event window and firing/resolved cycle before repeating; background events also count. The commands above record the source commit.

The three synthetic tests need explicit installation and deleteRules cleanup as described in their runbook. Their inputs are synthetic: they test state transitions and notification delivery, not real resource exhaustion. A real login alert was operator-tested manually; no credential-handling automated login script is included. 403/429 and traffic comparison are panels only.

For each run record date/time zone, commit, target, result, rule state/health, firing/resolved evidence and final recovery. Do not commit secrets or raw application logs.

The bounded 404 check is an authorized functional alert test, not a DDoS test. DoS targets service availability; DDoS uses multiple hosts/sources. Request count alone does not classify a test as an attack. Passing this test does not prove overload or DDoS resistance.

Sources: [NIST DDoS definition](https://csrc.nist.gov/glossary/term/distributed_denial_of_service), [CISA DoS/DDoS guidance](https://www.cisa.gov/sites/default/files/publications/understanding-and-responding-to-ddos-attacks_508c.pdf).
