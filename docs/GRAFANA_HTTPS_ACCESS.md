# Grafana HTTPS elérés a csapat számára

[English version](GRAFANA_HTTPS_ACCESS.en.md) · [Dokumentációjegyzék](README.md)

Előkészítve: **2026. november 11.** Ez az eljárás a Grafanát teszi böngészőből, saját Grafana-fiókkal elérhetővé. Nem ad Oracle-fiókot, SSH-kulcsot vagy parancssori hozzáférést a csapattársaknak. A hálózati közzététel és az egyetlen dashboardra szűkített Grafana-jogosultság két külön beállítás.

Tervezett cím: **https://grafana-r0cecq.duckdns.org/**. Az üzemeltető DNS-kimenete `130.162.254.233` IPv4-címet adott; a 80/443 porton nem volt hallgató szolgáltatás. Az INPUT lánc 5. szabálya REJECT volt, a netfilter-persistent aktív. Ezek dátumhoz kötött előellenőrzések, nem bizonyítják az alábbi telepítés sikerét.

## Felépítés

Böngésző → HTTPS TCP 443 → Caddy → HTTP 127.0.0.1:3000 → Grafana.

A `caddy:2.11.9-alpine` hivatalos, ARM64-et is támogató image a Compose **public** profiljában szerepel. Alapesetben továbbra is a hat monitoringkonténer indul; a Caddy külön, tudatos lépésben indítandó. Külön `caddy_data` és `caddy_config` volume őrzi a TLS- és működési állapotát. A Caddy admin API csak 127.0.0.1:2019-en figyel. Nincs Prometheus/Loki/exporter proxyútvonal; a Grafana végpontjai továbbra is a saját bejelentkezését és jogosultságait használják.

A Git-frissítés nem nyit tűzfalportot, nem indít Caddyt és nem írja át a privát .env-t. A Grafana alapbeállítása a három új változó nélkül a korábbi helyi HTTP-elérés marad.

## 1 Előellenőrzés és frissítés

Az Oracle VM-en:

```bash
cd ~/ai-job-monitoring
git status --short
# Csak áttekintett munkafával folytasd; ismert untracked exportokat nem kell törölni.
PREVIOUS_HTTPS_COMMIT=$(git rev-parse HEAD)
git pull --ff-only
sudo docker compose config --quiet

getent ahostsv4 grafana-r0cecq.duckdns.org
sudo ss -ltnp '( sport = :80 or sport = :443 )'
sudo iptables -L INPUT -n -v --line-numbers
sudo systemctl is-active netfilter-persistent
sudo systemctl list-timers --all | grep -Ei 'certbot|acme|caddy' || true
```

A név a tényleges Oracle publikus IP-re mutasson. Ha IPv6 AAAA rekord is van, annak is helyes, elérhető célra kell mutatnia; ezt külön ellenőrizd. A meglévő `matchwise-logs-r0cecq.duckdns.org` rekordot és TLS-fájlokat ne módosítsd. Ha régi certbot/ACME timer standalone 80-as portot igényel, a megújítását össze kell hangolni a Caddyvel; ne tiltsd le vakon.

## 2 Caddy ellenőrzése és a privát Grafana-beállítás

```bash
sudo docker compose --profile public pull caddy
sudo docker compose --profile public run --rm --no-deps --entrypoint caddy caddy \
  validate --config /etc/caddy/Caddyfile --adapter caddyfile

mkdir -p "$HOME/monitoring-private-backups"
GRAFANA_ENV_BACKUP="$HOME/monitoring-private-backups/grafana-env-before-https-$(date -u +%Y%m%dT%H%M%SZ)"
(umask 077; cp .env "$GRAFANA_ENV_BACKUP")
printf 'Privát env mentés: %s\n' "$GRAFANA_ENV_BACKUP"
nano .env
```

A .env-ben ezt a három beállítást add meg egyszer, a többi változó megőrzésével:

```dotenv
GRAFANA_PUBLIC_DOMAIN=grafana-r0cecq.duckdns.org
GRAFANA_PUBLIC_URL=https://grafana-r0cecq.duckdns.org/
GRAFANA_COOKIE_SECURE=true
```

Ne másold be a teljes .env-t chatbe vagy Gitbe. Az adminjelszó és Telegram-kulcs változatlan marad. A Compose a későbbi normál Grafana-újralétrehozáskor is innen kapja a külső címet és a secure cookie beállítást.

```bash
chmod 600 .env
sudo docker compose --profile public config --quiet
```

A secure cookie miatt normál böngészős bejelentkezésre ezután a HTTPS-címet használd; a sima HTTP-s localhost SSH-alagút nem megfelelő a bejelentkezési sütihez. Az SSH shell és a helyi health-lekérdezés ettől elérhető marad.

## 3 Oracle Cloud hálózati engedélyezés

A VM megfelelő VNIC-jéhez kapcsolódó NSG-ben vagy a subnethez tartozó Security Listben hozz létre két **stateful ingress** szabályt:

| Forrás | Protokoll | Forrásport | Célport | Leírás |
|---|---|---|---|---|
| 0.0.0.0/0 | TCP | All | 80 | Caddy HTTP redirect and certificate validation |
| 0.0.0.0/0 | TCP | All | 443 | Grafana HTTPS through Caddy |

A két szabályt a ténylegesen alkalmazott hálózati szabálykészletben kell felvenni; nem kell automatikusan minden NSG-be és Security Listbe duplikálni. A meglévő SSH- és egyéb szükséges szabályokat tartsd meg. 3000, 9090, 9100, 9115, 3100, 12345 és 2019 portokat ne tegyél nyilvánossá. UDP 443 nem szükséges ehhez az alap HTTP/1.1 és HTTP/2 eléréshez.

## 4 Ubuntu INPUT engedélyezés

Az alábbi parancsok a bemutatott INPUT-sorrendre épülnek: az 1–4. szabályt megtartják, és az 5. helyre szúrnak új ACCEPT szabályt a REJECT elé. Ha időközben más lett a sorrend, előbb vizsgáld meg, és ne használd változtatás nélkül a sorszámot.

```bash
GRAFANA_FIREWALL_BACKUP="$HOME/monitoring-private-backups/firewall-before-grafana-$(date -u +%Y%m%dT%H%M%SZ).v4"
(umask 077; sudo iptables-save > "$GRAFANA_FIREWALL_BACKUP")
printf 'Tűzfalmentés: %s\n' "$GRAFANA_FIREWALL_BACKUP"

sudo iptables -C INPUT -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT ||
  sudo iptables -I INPUT 5 -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT

sudo iptables -C INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT ||
  sudo iptables -I INPUT 5 -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT

sudo iptables -L INPUT -n -v --line-numbers
sudo netfilter-persistent save
```

A 22-es SSH ACCEPT megmarad. Nem használunk flush-t, policy-módosítást vagy teljes szabálycserét. A host hálózatos Caddy kapcsolatai az INPUT láncon mennek át; itt nincs Docker portpublikálás.

## 5 A két érintett szolgáltatás indítása

```bash
sudo docker compose --profile public up -d --no-deps --force-recreate grafana caddy
sudo docker compose --profile public ps grafana caddy
sudo docker compose --profile public logs --since=10m --tail=150 caddy grafana
```

A Grafana röviden újraindul. A többi monitoringkonténert és a collectort ez a parancs nem indítja újra. Az anonim hozzáférés és az önálló regisztráció továbbra is tiltott. A Caddy elindítja a tanúsítványigénylést; ehhez a DNS, a host- és az Oracle-hálózati engedélyezés együtt szükséges. A tanúsítványadat-volume-ot ne töröld rutinszerűen.

## 6 Ellenőrzés és csapatfiókok

```bash
curl -fsS http://127.0.0.1:3000/api/health
curl -I http://grafana-r0cecq.duckdns.org/
curl -fsS https://grafana-r0cecq.duckdns.org/api/health
curl -I https://grafana-r0cecq.duckdns.org/login
sudo ss -ltnp '( sport = :80 or sport = :443 or sport = :3000 or sport = :2019 )'
```

Várt: helyi és HTTPS Grafana health sikeres; HTTP átirányítás HTTPS-re; login 200; 3000 és 2019 loopbacken. Külön, nem az Oracle gépről is nyisd meg a címet: a VM saját publikus IP-jére indított ellenőrzés önmagában nem bizonyít külső elérést. Ne használd a curl -k opciót végső TLS-bizonyítéknak.

Ezután hozz létre saját jelszavas Viewer-fiókokat a csapattársaknak. A kijelölt dashboard/mappa engedélyeit és az örökölt Viewer-jogokat külön állítsd be; a HTTPS önmagában nem korlátozza a hozzáférést egyetlen dashboardra. Az alap Viewer adatforrás-lekérdezési jogosultsága sem panelenkénti adatelkülönítés. Adminfiókot vagy SSH-kulcsot nem kell átadni. Egy Viewer böngészős bejelentkezésével ellenőrizd a kívánt láthatóságot, a szerkesztés tiltását és a Grafana Live kapcsolatot.

## Hibakeresés és visszaállítás

- HTTPS timeout: DNS, OCI ingress, INPUT-sorrend, Caddy állapot.
- Tanúsítványigénylési hiba: A/AAAA cél, 80/443 elérhetőség, Caddy napló és esetleges korábbi ACME rate limit; ne indítsd újra folyamatosan.
- 502: a Grafana 127.0.0.1:3000 végpontja és a konténer állapota.
- Hibás átirányítás/bejelentkezés: a .env három nyilvános beállítása, végső HTTPS-cím, böngészős sütik; a domain egyezzen a Caddyfile-lal.
- A 12 korábbi szabály helyi szolgáltatásokat és külső alkalmazásokat figyel; nem ad külön bizonyítékot a publikus Caddy/DNS/tanúsítvány út teljes működéséről.

Visszaállításkor állítsd le a Caddyt, majd a .env három értékét állítsd vissza:

```bash
sudo docker compose --profile public stop caddy
nano .env
```

```dotenv
GRAFANA_PUBLIC_DOMAIN=localhost
GRAFANA_PUBLIC_URL=http://localhost:3000/
GRAFANA_COOKIE_SECURE=false
```

```bash
sudo docker compose config --quiet
sudo docker compose up -d --no-deps --force-recreate grafana
curl -fsS http://127.0.0.1:3000/api/health
```

Csak az e bevezetés során felvett, alábbi specifikációjú tűzfalszabályokat távolítsd el, ha korábban nem léteztek:

```bash
sudo iptables -D INPUT -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT
sudo iptables -D INPUT -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
sudo netfilter-persistent save
```

Az OCI-ben is csak a most hozzáadott két ingress szabályt vond vissza. Ne tölts vissza vakon teljes régi iptables-mentést futó Docker mellett. A Caddy/Grafana volume és a collector állapota megmarad; a privát env-mentésből csak áttekintés után állíts vissza, nehogy későbbi kulcsmódosításokat elveszíts.

## Állapot és források

Helyi ellenőrzés: alap Compose továbbra is hat szolgáltatást aktivál, a public profil érvényes; a hivatalos 2.11.9 Caddy validálta a Caddyfile-t. Az image ARM64 támogatása az official-images leírásban ellenőrizve. **Oracle-telepítés, portnyitás, tanúsítványigénylés és böngészős bejelentkezés még nem igazolt.**

- [Caddy HTTPS](https://caddyserver.com/docs/automatic-https)
- [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
- [Grafana reverse proxy](https://grafana.com/tutorials/run-grafana-behind-a-proxy/)
- [Oracle security rules](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm)
