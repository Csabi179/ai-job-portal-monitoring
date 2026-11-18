# A 12 Grafana-riasztás kézi tesztelése

> **Új, még nem telepített frissítés (2026-11-18):** a fejlesztési ág 16 állandó szabályt, 35 Service Comparison panelt és percenkénti backendpróbát tartalmaz (60s/15s/10s, 3 perces frissesség). A korábban igazolt éles állapot 15 szabályos; az új frissítés éles ellenőrzése és telepítése még hátravan. [Ellenőrzés és alkalmazás](SECURITY_OVERVIEW_AND_FREQUENT_PROBES.md).

**Hatókör:** ez az eredeti 12 szabály tesztleírása. A jelenlegi készlet 15 állandó szabály; az új három külön [tesztleírásban](SERVICE_COMPARISON_ALERT_TEST.md) és [tesztnaplóban](monitoring-tests.md#test-20-synthetic-security-alert-cycle) szerepel.

**Jelenlegi alkalmazás:** az alábbi szabálylogika továbbra is az eredeti 12 provisionált szabályhoz tartozik; a HTTP-célok és a kivárási idők nem változtak. A Grafana normál elérése HTTPS-en történik, a Telegram-cél a csapat csoportja. A collector és Node Exporter élő tesztje igazolt; a többi tíz szabály tesztelési eljárása nem jelent elvégzett tesztet. Lásd [aktuális állapot és tesztek](monitoring-tests.md).


[English version](alert-rule-tests.en.md) · [Dokumentációjegyzék](README.md)

Helyi tesztsegéd: [docs/testing/alert-rule-test-helper.py](testing/alert-rule-test-helper.py).

A `41c3f8d` konfigurációhoz készült útmutató. **A dokumentum létrehozásakor nem futtattunk új élő tesztet.** Korábban igazolt: collector Firing/Resolved, Node Exporter `up=0` → Firing → `up=1` → Resolved. A többi itt leírt eljárás terv; a helyi ellenőrzés nem Oracle- vagy Telegram-teszt. Bizonyíték: [tesztnapló](monitoring-tests.md).

Minden parancs az **Oracle Ubuntu VM-en**, Bash alatt futtatandó. Egyszerre egy tesztet végezz, és minden teszt végén állítsd vissza a működést. A Grafanát ne indítsd újra teszt közben: a pending idő újraindulhat.

## Mit vizsgálunk?

| # | Szabály UID | Bemenet előállítása | Pending |
|---|---|---|---|
| 1 | matchwise_node_exporter_unavailable | Node Exporter leállítása | 3m |
| 2 | ai_job_exporter_down | Blackbox Exporter leállítása | 3m |
| 3 | matchwise_prometheus_scrape_unavailable | Csak az önscrape átirányítása helyi HTTP 503-ra | 3m |
| 4 | matchwise_backend_down | Blackbox helyi HTTP 503-at mér, az eredeti sorcímkékkel | 2m |
| 5 | matchwise_backend_probe_missing | Backend scrape helyi HTTP 503-ra irányítva: up=0 | 2m |
| 6 | matchwise_frontend_down | Blackbox helyi HTTP 503-at mér | 2m |
| 7 | matchwise_frontend_probe_missing | Frontend scrape helyi HTTP 503-ra irányítva: up=0 | 2m |
| 8 | matchwise_supabase_metrics_unavailable | Metrics scrape helyi HTTP 503-at kap | 3m |
| 9 | matchwise_supabase_database_down | Helyi metrikaforrás: up=1, pg_up=0 | 2m |
| 10 | matchwise_render_collector_stale | Collector timer leállítása | 2m, a >300s heartbeat-kor után |
| 11 | matchwise_loki_health_unavailable | Loki leállítása | 3m |
| 12 | matchwise_alloy_health_unavailable | Alloy leállítása | 3m |

Az 1/2/10/11/12 teszt valódi monitoringkomponenst szüneteltet. A 3–9 teszt a változatlan éles szabályt ellenőrzi ellenőrzött helyi bemenettel, nem a távoli alkalmazás/DB tényleges leállását. A tesztbemenet a normál Prometheus-idősorokba kerül, ezért jegyezd fel a tesztidőszakot; annak mintáit ne tekintsd valós alkalmazás-rendelkezésreállásnak. A helper nem módosít riasztási szabályt, tokent, SQLite-ot vagy Docker-volume-ot.

## 0. Közös előkészítés

Az útmutatót tartalmazó commitot előbb töltsd le. Vizsgáld meg a `git status` kimenetét; az ismert untracked exportok megmaradhatnak, de helyi konfigurációeltérést előbb rendezz.

```bash
cd ~/ai-job-monitoring
git status --short
git pull --ff-only
git diff --exit-code -- prometheus/prometheus.yml
sudo docker compose config --quiet
sudo docker compose ps
sudo systemctl is-active matchwise-render-logs.timer
```

Minden szolgáltatás működjön; a collector timer legyen `active`, a 12 szabály friss értékelés mellett Normal. Az esetleg kezdeti KeepLast/Normal állapot nem UP-bizonyíték.

A helyi tesztforrást csak a 3–9 tesztekhez kell elindítani. Ellenőrizd a PyYAML-t; hiánya esetén telepítsd az Ubuntu csomagot:

```bash
python3 -c 'import yaml; print(yaml.__version__)'
# Csak ha a fenti import hiányzó modulra fut:
# sudo apt-get update
# sudo apt-get install -y python3-yaml
```

Privát, egyedi konfigurációmentés és loopback tesztszerver; a 19199-es portot ne nyisd meg az internet felé:

```bash
mkdir -p "$HOME/monitoring-private-state"
ALERT_TEST_STATE=$(mktemp -d "$HOME/monitoring-private-state/alert-rules.XXXXXX")
printf 'Privát tesztmentés: %s\n' "$ALERT_TEST_STATE"
sudo python3 docs/testing/alert-rule-test-helper.py init --state "$ALERT_TEST_STATE"

sudo systemd-run --unit=matchwise-alert-fixture --collect \
  --property=User=ubuntu --property=Group=ubuntu --property=RuntimeMaxSec=2h \
  /usr/bin/python3 "$PWD/docs/testing/alert-rule-test-helper.py" serve

curl -fsS http://127.0.0.1:19199/http-ok
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:19199/http-fail
```

Várt eredmény: `Local alert test recovered`, illetve `HTTP 503`. Ha az egységnév/port már foglalt, előbb vizsgáld meg a korábbi tesztet; ne írj felül más folyamatot. A 2h a tesztszerver élettartama, **nem automatikus konfiguráció-visszaállítás**.

Ugyanebben az SSH-shellben definiáld a rövidítéseket. A helper minden módot az eredeti mentésből állít elő, és idegen konfigurációmódosítás esetén megtagadja a felülírást.

```bash
pq() {
  curl -fsSG http://127.0.0.1:9090/api/v1/query \
    --data-urlencode "query=$1" | python3 -m json.tool
}

apply_test_config() {
  sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
    check config /etc/prometheus/prometheus.yml &&
  sudo docker compose up -d --no-deps --force-recreate prometheus
}

inject() {
  sudo python3 docs/testing/alert-rule-test-helper.py prepare "$1" \
    --state "$ALERT_TEST_STATE" && apply_test_config
}

restore_prom() {
  sudo python3 docs/testing/alert-rule-test-helper.py restore \
    --state "$ALERT_TEST_STATE" && apply_test_config
}
```

A fixture scrape-ok **60s** gyakoriságúak, a most előkészített éles backend/frontendsűrűséggel egyezően, az eredeti instance/service címkéket megtartva. Backend HTTP-tesztnél kizárólag a helyi teszt-URL kap sűrűbb lekérést, nem a Render szolgáltatás. Az eredeti példánycímke megtartása szükséges, különben egy más címkéjű hibás minta 3 percig bent maradhatna a szolgáltatásszabály ablakában. Supabase-helyettesítésnél a helper kihagy minden Basic Auth/secret/file_sd beállítást: kulcsot nem küld a tesztszervernek.

Általában 60–90s után jelenik meg az új minta; utána pending és értékelés következik. Új értesítési csoportnál 30s, meglévő csoport változásánál akár 5m plusz várakozás lehet. A lent megadott 2–5m becslésekhez ez hozzáadódhat. Minden tesztnél ellenőrizd a Grafana Pending/Firing/Normal állapotát és a megfelelő Telegram firing/resolved üzenetet. Nem szükséges az ismétlési 4 órát kivárni.

## 1. Oracle host metrics — matchwise_node_exporter_unavailable

```bash
sudo docker compose stop node-exporter
# 60–90s után:
pq 'up{job="node_exporter"}'
```

**Várt:** `up=0`, 3m pending után `MatchWise | Oracle host metrics | Monitoring failure` firing; rendszerint 3–5m + csoportvárakozás. A collector szabály KeepLast állapotban maradhat; a collector maga tovább futhat.

```bash
sudo docker compose start node-exporter
# 60–90s után:
pq 'up{job="node_exporter"}'
```

**Helyreállás:** `up=1`, Normal és resolved. Ezt a teljes ciklust az üzemeltető már igazolta.

## 2. Blackbox Exporter — ai_job_exporter_down

```bash
sudo docker compose stop blackbox-exporter
# 60–90s után:
pq 'up{job="blackbox_exporter"}'
```

**Várt:** `up=0`, 3m pending után `MatchWise | Blackbox Exporter | Monitoring failure` firing. Más HTTP/health monitoringhibák is megjelenhetnek; ez közös függőségi hiba, a szabályok nem végeznek automatikus elnyomást. A backend scrape ritkább, nem biztos, hogy a rövid teszt alatt lefut.

```bash
sudo docker compose start blackbox-exporter
# 60–90s után:
pq 'up{job="blackbox_exporter"}'
pq 'probe_success{job="blackbox_monitoring_components"}'
```

**Helyreállás:** saját `up=1`, loki/alloy próbák 1, Blackbox resolved. Minden más, a teszt alatt keletkezett riasztást is ellenőrizz; a backend következő természetes próbájáig akár 30m lehet.

## 3. Prometheus self-check — matchwise_prometheus_scrape_unavailable

```bash
inject prometheus-scrape-fail
# 60–90s után:
curl -fsS http://127.0.0.1:9090/-/ready
pq 'up{job="prometheus"}'
```

**Várt:** a lekérdezési API továbbra is működik, de az önscrape `up=0`; 3m pending után `MatchWise | Prometheus self-check | Monitoring failure` firing. A teljes Prometheus leállítása más teszt lenne: DatasourceError, nem ez a szabály.

```bash
restore_prom
# 60–90s után:
pq 'up{job="prometheus"}'
```

**Helyreállás:** `up=1`, Normal és resolved.

## 4. Render backend HTTP — matchwise_backend_down

```bash
inject backend-http-fail
# 60–90s után:
pq 'last_over_time(up{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
pq 'last_over_time(probe_success{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
```

**Várt:** `up=1`, `probe_success=0`; 2m pending után `MatchWise | Render backend | HTTP outage` firing. A backend monitoringhiba-szabály nem ettől az állapottól riaszt. A tényleges Render szolgáltatást nem állítjuk le.

```bash
inject backend-http-ok
# 60–90s után:
pq 'last_over_time(probe_success{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
# Várd meg a Normal/resolved állapotot, azután:
restore_prom
```

**Helyreállás:** ugyanazon idősor helyi sikeres próbája 1-re vált és resolved érkezik; utána visszaáll az eredeti 30m Render-próba. A tesztből maradt sikeres minta nem bizonyít Render-UP állapotot: a következő eredeti, ütemezett scrape-ot külön ellenőrizd.

## 5. Render backend monitoring — matchwise_backend_probe_missing

```bash
inject backend-scrape-fail
# 60–90s után:
pq 'last_over_time(up{job="blackbox_render_backend",service="matchwise_backend"}[3m])'
```

**Várt:** `up=0`; 2m pending után `MatchWise | Render backend | Monitoring failure` firing. Ez scrape-hiba, nem igazolt HTTP-kiesés; a HTTP-szabály KeepLast marad.

```bash
inject backend-http-ok
# Várd meg az up=1, probe_success=1 és resolved állapotot, azután:
restore_prom
```

**Hiányzó adatos ág, opcionális külön teszt:** `inject backend-absent`, majd `pq 'absent_over_time(up{job="blackbox_render_backend",service="matchwise_backend"}[3m])'`. A még meglévő minta miatt eleinte üres az eredmény; 3m-nél régebbi utolsó mintánál 1, majd 2m pending után firing várható. Teljes idő kb. 5–7m + csoportvárakozás. Ne rövidítsd le a szabály 3m ablakát a teszt kedvéért. Visszaállítás: `inject backend-http-ok`, resolved után `restore_prom`.

## 6. Vercel frontend HTTP — matchwise_frontend_down

```bash
inject frontend-http-fail
# 60–90s után:
pq 'last_over_time(up{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'
pq 'last_over_time(probe_success{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'
```

**Várt:** `up=1`, `probe_success=0`; 2m pending után `MatchWise | Vercel frontend | HTTP outage` firing.

```bash
inject frontend-http-ok
# Várd meg a probe_success=1 és resolved állapotot, azután:
restore_prom
```

**Helyreállás:** Normal/resolved, majd a visszaállított eredeti frontendcél következő 60s scrape-ja ismét legyen sikeres.

## 7. Vercel frontend monitoring — matchwise_frontend_probe_missing

```bash
inject frontend-scrape-fail
# 60–90s után:
pq 'last_over_time(up{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'
```

**Várt:** `up=0`; 2m pending után `MatchWise | Vercel frontend | Monitoring failure` firing; a HTTP-szabály nem kap bizonyított új HTTP-hibát.

```bash
inject frontend-http-ok
# Várd meg az up=1, probe_success=1 és resolved állapotot, azután:
restore_prom
```

**Hiányzó adatos ág, opcionális:** `inject frontend-absent`, majd `pq 'absent_over_time(up{job="blackbox_vercel_frontend",service="matchwise_frontend"}[3m])'`. 3m mintahiány után 1, további 2m pending után firing, kb. 5–7m + csoportvárakozás. Visszaállítás: `inject frontend-http-ok`, resolved után `restore_prom`.

## 8. Supabase metrics — matchwise_supabase_metrics_unavailable

```bash
inject supabase-metrics-fail
# 60–90s után:
pq 'up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
```

**Várt:** `up=0`; 3m pending után `MatchWise | Supabase | Monitoring failure` firing. A PostgreSQL-szabály KeepLast; valódi DB-kiesést ez nem bizonyít.

```bash
inject supabase-ok
# 60–90s után:
pq 'pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
# Várd meg az up=1, pg_up=1 és resolved állapotot, azután:
restore_prom
```

**Helyreállás:** előbb a helyi tesztforrás, majd restore után a valódi Supabase up/pg_up értéke is 1. Kulcsot nem módosítunk és nem íratunk ki.

## 9. Supabase PostgreSQL — matchwise_supabase_database_down

```bash
inject supabase-db-fail
# 60–90s után:
pq 'up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
pq 'pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
```

**Várt:** `up=1`, `pg_up=0`; 2m pending után `MatchWise | Supabase PostgreSQL | Connectivity failure` firing. A Metrics API monitoringhiba-szabály nem ettől az állapottól riaszt. Ez mesterséges pg_up-bemenet; nem állítja le és nem teszteli a valódi PostgreSQL-t, Authot vagy PostgREST-et.

```bash
inject supabase-ok
# Várd meg az up=1, pg_up=1 és resolved állapotot, azután:
restore_prom
```

**Helyreállás:** Normal/resolved; restore után ellenőrizd a valódi Supabase két metrikáját is.

## 10. Render log collector — matchwise_render_collector_stale

```bash
sudo systemctl stop matchwise-render-logs.timer
sudo systemctl is-active matchwise-render-logs.timer
sudo systemctl is-active matchwise-render-logs.service
pq 'max(time() - matchwise_render_collector_last_success_timestamp_seconds{job="node_exporter"})'
```

**Várt:** timer `inactive`; folyó oneshot esetén várd meg annak végét, ne öld meg írás közben. Heartbeat-kor >300s, Node Exporter up=1, további 2m pending után `MatchWise | Render log collector | Monitoring failure` firing; kb. 7–10m + csoportvárakozás az utolsó sikeres futástól. Az `is-active` inactive esetén nem nulla exitkódja itt várt.

```bash
sudo systemctl start matchwise-render-logs.service
sudo systemctl start matchwise-render-logs.timer
sudo systemctl show matchwise-render-logs.service -p Result -p ExecMainStatus
sudo systemctl is-active matchwise-render-logs.timer
# 60–90s után:
pq 'max(time() - matchwise_render_collector_last_success_timestamp_seconds{job="node_exporter"})'
pq 'node_textfile_scrape_error{job="node_exporter"}'
```

**Helyreállás:** success/0, timer active, friss heartbeat, textfile hiba 0, Normal/resolved. A Firing/Resolved ciklus már igazolt; ne töröld a heartbeatet, SQLite-ot vagy a kurzort. Ez nem önmagában Loki-kézbesítési teszt.

## 11. Loki health — matchwise_loki_health_unavailable

```bash
sudo docker compose stop loki
# 60–90s után:
pq 'up{job="blackbox_monitoring_components",service="loki"}'
pq 'probe_success{job="blackbox_monitoring_components",service="loki"}'
```

**Várt:** up=1, probe_success=0, 3m pending után `MatchWise | Loki | Health check failure` firing. Loki írás/lekérdezés szünetel, Alloy továbbítási hibákat/retry-t jelezhet; ez a teszt nem garantál adatvesztésmentességet.

```bash
sudo docker compose start loki
curl -fsS http://127.0.0.1:3100/ready
# Indulási 503/kapcsolódási hiba esetén később ismételd a curl-t.
# 60–90s után:
pq 'probe_success{job="blackbox_monitoring_components",service="loki"}'
```

**Helyreállás:** ready, probe_success=1, Normal/resolved. Külön ellenőrizd az Alloy és a naplóút működését; a health-válasz önmagában nem kézbesítési bizonyíték.

## 12. Alloy health — matchwise_alloy_health_unavailable

```bash
sudo docker compose stop alloy
# 60–90s után:
pq 'up{job="blackbox_monitoring_components",service="alloy"}'
pq 'probe_success{job="blackbox_monitoring_components",service="alloy"}'
```

**Várt:** up=1, probe_success=0, 3m pending után `MatchWise | Alloy | Health check failure` firing. A collector tovább gyűjthet JSONL-be, de a Loki felé továbbítás szünetel.

```bash
sudo docker compose start alloy
curl -fsS http://127.0.0.1:12345/-/healthy
# Ha még indul, később ismételd a curl-t.
# 60–90s után:
pq 'probe_success{job="blackbox_monitoring_components",service="alloy"}'
```

**Helyreállás:** healthy, probe_success=1, Normal/resolved. Az Alloy-volume és olvasási pozíciók megmaradnak; a valós naplókézbesítést külön vizsgáld.

## Lezárás és félbehagyott teszt visszaállítása

Ha bármelyik inject/validálás hibázik, ne folytasd másik teszttel. Ugyanebben a shellben `restore_prom`, majd vizsgáld meg az állapotot. Új SSH-sessionnél állítsd vissza az `ALERT_TEST_STATE` változóba a korábban kiírt konkrét privát könyvtárat, definiáld újra a függvényeket, vagy futtasd közvetlenül:

```bash
# A helyőrzőt a saját korábban kiírt könyvtáradra cseréld:
# ALERT_TEST_STATE="$HOME/monitoring-private-state/alert-rules.XXXXXX"
sudo python3 docs/testing/alert-rule-test-helper.py restore --state "$ALERT_TEST_STATE"
sudo docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml
# Csak sikeres validálás után:
sudo docker compose up -d --no-deps --force-recreate prometheus
```

Ha idegen konfigurációmódosítás miatt a helper megtagadja a visszaállítást, előbb hasonlítsd össze a privát mentést és a jelenlegi fájlt; ne használj reset --hard-ot.

Az összes elvégzett teszt után:

```bash
restore_prom
sudo docker compose start node-exporter blackbox-exporter loki alloy
sudo systemctl start matchwise-render-logs.timer
sudo systemctl is-active matchwise-render-logs.timer
sudo systemctl stop matchwise-alert-fixture.service
git diff --exit-code -- prometheus/prometheus.yml
sudo docker compose ps
pq 'up{job="node_exporter"}'
pq 'up{job="blackbox_exporter"}'
pq 'up{job="prometheus"}'
pq 'probe_success{job="blackbox_monitoring_components"}'
pq 'up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
pq 'pg_up{job="supabase",instance="uvopvarvelpabhmrqaaw.supabase.co:443"}'
```

Ha a helyi tesztforrást nem indítottad, annak hiányzó systemd egysége nem új alkalmazáshiba. A privát mentést őrizd meg az ellenőrzés végéig. Üres/0 minta nem siker; a visszaállított backend természetes próbájáig akár 30m is kellhet. Minden teszt végén legyenek lezárva a hozzá tartozó Grafana/Telegram események.

A [tesztnaplóban](monitoring-tests.md) rögzítsd a dátumot/időzónát, commitot, UID-t, a tényleges vagy szintetikus bemenetet, query eredményt, Firing/Resolved kézbesítést és a visszaállított állapotot. Egy teszt sikere nem jelenti mind a 12 sikerét. A teljes VM/Grafana-kieséshez független külső ellenőrzés szükséges; azt ezek a szabályok nem helyettesítik.
