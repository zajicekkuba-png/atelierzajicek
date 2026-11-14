# Ateliér Zajíček – návod

## 1. Jednorázové nastavení (asi 30 minut)

### GitHub
1. Založte si účet na **github.com** (zdarma).
2. Vpravo nahoře **+ → New repository**. Název: `atelierzajicek`, zvolte **Public**, nic dalšího nezaškrtávejte. Klikněte **Create repository**.
3. Na stránce prázdného repozitáře klikněte na odkaz **uploading an existing file**.
4. Rozbalte ZIP a přetáhněte do okna **celý obsah složky** (soubory i složky `fotky`, `scripts`, `.github`).
   - Složka `.github` je na Macu skrytá. Ve Finderu ji zobrazíte zkratkou **Cmd + Shift + .**
   - Když se ji nepodaří nahrát: **Add file → Create new file**, jako název napište `.github/workflows/web.yml` a vložte obsah stejnojmenného souboru ze ZIPu.
5. Dole klikněte **Commit changes**.
6. **Settings → Pages → Build and deployment → Source:** vyberte **GitHub Actions**.
7. Záložka **Actions**: web se sestavuje (žlutá tečka). Po 1–3 minutách se objeví zelená fajfka. Web běží na adrese `https://VASE-JMENO.github.io/atelierzajicek/`.

### Doména atelierzajicek.cz
1. Na GitHubu **Settings → Pages → Custom domain**: napište `atelierzajicek.cz` a dejte **Save**.
2. Na VEDOSu otevřete u domény **DNS záznamy**. Smažte stávající záznamy typu A, AAAA a CNAME pro doménu a `www` a přidejte:

| Typ | Název | Hodnota |
|---|---|---|
| A | (prázdné / @) | 185.199.108.153 |
| A | (prázdné / @) | 185.199.109.153 |
| A | (prázdné / @) | 185.199.110.153 |
| A | (prázdné / @) | 185.199.111.153 |
| CNAME | www | VASE-JMENO.github.io |

3. Počkejte (obvykle do pár hodin, výjimečně až 24 h). Až GitHub v **Settings → Pages** napíše, že je DNS v pořádku, zaškrtněte **Enforce HTTPS**.

## 2. Přidávání fotek

1. Na GitHubu otevřete složku `fotky` a v ní kategorii, např. `portrety`.
2. **Add file → Upload files**, přetáhněte fotky, dole **Commit changes**.
3. Za 1–3 minuty jsou fotky na webu: zmenšené, zařazené a nejnovější první.

**Kategorie** = složka ve `fotky`: `produkt`, `portrety`, `reportaz`, `architektura`, `priroda`, `design`. Novou kategorii vytvoříte novou složkou.

**Projekt z více fotek** = podsložka v kategorii, např. `fotky/produkt/topadroit-kampan/`.
- Vytvoření: ve složce kategorie **Add file → Create new file**, napište `topadroit-kampan/nazev.txt` (lomítko vytvoří složku) a do souboru napište hezký název, třeba `Kampaň TOPADROIT 2026`. Pak do nové složky nahrajte fotky.
- Návštěvník pak po kliknutí na fotku prolistuje celý projekt.

**Název fotky**: když se soubor jmenuje hezky (např. `Ostrava večer.jpg`), použije se jako název. Názvy z fotoaparátu (`IMG_1234`, `DSC_…`) se nezobrazí.

**Smazání fotky**: otevřete ji na GitHubu → tři tečky vpravo nahoře → **Delete file** → **Commit changes**.

**Tipy**
- Nahrávejte JPG o velikosti do pár MB (delší strana kolem 3000 px). Přes web jde nahrát soubor do 25 MB.
- Fotky z iPhonu (HEIC) web převede sám.
- Na mobilu jde nahrávat v prohlížeči na github.com.

## 3. Úpravy textů
Texty (O mně, praxe, kontakty, odkazy na sociální sítě) jsou v souboru `index.html`. Otevřete ho na GitHubu, klikněte na tužku, upravte a **Commit changes**. Odkazy na Instagram, Facebook a LinkedIn najdete hledáním `instagram.com`, `facebook.com`, `linkedin.com`.

Portrétní fotka v sekci „Kdo jsem?“ je soubor `profil.jpg`. Nahrajte nový soubor se stejným názvem a starý se nahradí.
