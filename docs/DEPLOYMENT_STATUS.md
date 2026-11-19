# Deployment status / Telepítési állapot

Updated / Frissítve: **2026-11-19**.

## Magyar

**A már átadott monitoringváltozások alkalmazva vannak az Oracle-on az üzemeltető visszajelzése alapján. A mostani main merge miatt nincs további telepítési vagy újrafuttatási feladat.**

Az üzemeltető pontosítása: minden átadott módosítást rögtön lefuttatott. Ez az aktuális telepítési állapot forrása; nem új, közvetlen SSH-ellenőrzés eredménye.

- A `feat/service-comparison` ág 113 commitja fast-forwarddal bekerült a monitoringrepó `main` ágába, a `10f43d1c6b770a0ac5ca91a297d83d0b3dad3062` commitig. A GitHub main állapotát külön visszaellenőriztük.
- Az Oracle-frissítések a korábban átadott, ellenőrzött telepítőkkel és fájlmásolásokkal már megtörténtek. A merge ezeket a meglévő változásokat rendezte a főágba; nem hozott új futásidejű konfigurációt.
- A visszaigazolás a legutóbbi módosításokra is vonatkozik: az API-hívások kiválasztott időablakra számított becsült összesítésére, a frontend host CPU-/memóriakártyák eltávolítására és a felső magyarázatra.
- A frontend éles automatikus telemetriája korábban külön igazolt: sikeres PR #11 merge/deploy, ismételt HTTP 204 küldések, valódi API-csomagok és Grafana/Prometheus-adatok.
- Az Oracle checkout korábban rögzített HEAD-je nem a telepített fájlok jelenlegi verziójának bizonyítéka. A fájlonkénti telepítéshez nem kellett a checkoutot átállítani vagy tisztára törölni. Az aktuális checkout HEAD-jéről nem készült új leltár.

**Most nem kell telepítőt ismét futtatni, konténert újraindítani vagy `git pull`/reset parancsot kiadni a merge miatt.** Ez a dokumentációs pontosítás sem változtat programot, dashboardot, metrikát vagy szolgáltatáskonfigurációt.

A repóban megmaradó telepítési parancsok új géphez, tudatosan választott későbbi frissítéshez vagy helyreállításhoz használhatók. A régi dátumozott „pending”, „még nincs telepítve” és „nincs main merge” bejegyzések az akkori munkafázist rögzítik, nem aktuális teendők.

Későbbi, valóban új futásidejű változáshoz továbbra is ellenőrzött alkalmazás szükséges, mert nincs automatikus GitHub → Oracle deploy. Ez nem jelenti a már alkalmazott verzió újratelepítését.

A telepítés visszaigazolása nem állítja, hogy minden opcionális riasztási hibainjektálás, Viewer-jogosultsági próba vagy teljes katasztrófa-helyreállítási teszt is megtörtént. Ezeknek saját bizonyítékuk van a [tesztnaplóban](monitoring-tests.md).

## English

**The operator confirmed every supplied monitoring update had already been applied on Oracle as it was delivered. The completed main merge does not require another deployment, installer run, container restart or working-tree reset.**

Monitoring `main` was independently verified at `10f43d1c6b770a0ac5ca91a297d83d0b3dad3062`, after a fast-forward of the 113 feature commits. Runtime changes had already been applied through the reviewed helpers and file copies, including the latest selected-period API total and removal of unavailable frontend host resource cards. The merge consolidated existing history; it did not introduce a new runtime revision to apply.

This deployment confirmation comes from the operator's statement, not a fresh SSH audit. The current Oracle checkout HEAD was not re-inventoried and must not be confused with the versions of individually deployed files. The separate production-browser telemetry path had already been verified through frontend PR #11, deployment, real API batches and Grafana/Prometheus observations.

Installation instructions remain for future runtime changes, fresh-host setup and recovery. Earlier dated pending/no-merge entries describe their historical stage and are superseded by this status. There is no automatic GitHub-to-Oracle deployment, so a genuinely new future runtime revision still needs controlled application; the already applied revision does not need to be replayed after this merge. Optional fault-injection and recovery tests retain their separate evidence limits.
