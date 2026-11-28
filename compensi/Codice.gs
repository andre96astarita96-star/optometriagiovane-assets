/**
 * Optometria Giovane – Compensi docenti
 * Legge gli ordini completati da WooCommerce e calcola il compenso di ogni docente.
 * Schede: Docenti, Pacchetti, Vendite, Compensi, Pagamenti.
 * Autore: Andrea Astarita
 */

var SITO = 'https://www.optometriagiovane.it';
var TITOLARE = 'Andrea Astarita';

/* ---------- Menu ---------- */
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Compensi docenti')
    .addItem('1. Prepara il foglio', 'preparaFoglio')
    .addItem('2. Collega WooCommerce', 'collegaWooCommerce')
    .addItem('3. Aggiorna adesso', 'aggiornaVendite')
    .addItem('4. Attiva aggiornamento automatico (ogni notte)', 'attivaAggiornamentoAutomatico')
    .addToUi();
}

/* ---------- Dati iniziali ---------- */
// [ID prodotto, Corso, Prezzo pieno, Docente, % al docente]
var DOCENTI_INIZIALI = [
  [11972, 'Avanzato: Optometria Pediatrica', 249, 'Stefano Gianesin', 0.5],
  [11826, 'Avanzato: Anomalie della Visione Binoculare', 249, 'Stefano Gianesin', 0.5],
  [11424, 'Masterclass | Lampada a fessura', 89, 'Marta Mosci', 0.5],
  [11039, 'Masterclass | Opto Sales Master', 219, 'Marko Jablanovic', 0.5],
  [10581, 'Base | Lenti a contatto Morbide', 229, 'Giulia Quarta', 0.5],
  [10525, 'Base | Lenti a contatto RGP', 349, 'Pietro Viglietti', 0.5],
  [10476, 'Base | Lenti a contatto sclerali', 149, 'Alessandro Piovanelli', 0.5],
  [10394, 'Base | Lampada a Fessura', 59, 'Maria Giulia Muzzi', 0.5],
  [10379, 'Base | Topografia Corneale', 69, 'Maria Giulia Muzzi', 0.5],
  [9396, 'Avanzato | Ortocheratologia', 647, 'Charles Di Benedetto', 0.5],
  [9322, 'Ortocheratologia | Corso Premium', 897, 'Charles Di Benedetto', 0.5],
  [9284, 'Masterclass | Lenti a contatto Morbide Multifocali', 297, 'Marco Di Somma', 0.5],
  [9124, 'Avanzato | Visual Training Optometrico', 1497, 'Nicola Rizzieri', 0.5],
  [12323, 'Formazione su Misura sull\'Esame Visivo', 350, TITOLARE, 0],
  [11283, 'Avanzato | In presenza | Neuro Optometria', 789, TITOLARE, 0],
  [11042, 'Masterclass | Lenti a contatto morbide Custom', 0.5, TITOLARE, 0],
  [10449, 'Webinar | Test per Forie', 39, TITOLARE, 0],
  [10447, 'Webinar | Anamnesi Perfetta', 39, TITOLARE, 0],
  [10443, 'Webinar | L\'addizione perfetta', 39, TITOLARE, 0],
  [9660, 'Lenti progressive | Corso Base', 79.99, TITOLARE, 0],
  [9635, 'Base | Optometria & Lavoro', 299, TITOLARE, 0],
  [9375, 'Masterclass | Lenti progressive', 234, TITOLARE, 0],
  [9110, 'Base | La Prescrizione dell\'astigmatismo', 159, TITOLARE, 0],
  [9096, 'Masterclass | Dominanza Oculare', 84, TITOLARE, 0],
  [47, 'Corso Optometria & Lavoro + 2h di consulenza', 499, TITOLARE, 0]
];

// [ID pacchetto, Nome pacchetto, ID corso 1, ID corso 2]
var PACCHETTI_INIZIALI = [
  [11338, 'Webinar Test per Forie / Anamnesi Perfetta', 10449, 10447],
  [11340, 'Webinar Test per Forie / Addizione Perfetta', 10449, 10443],
  [11344, 'Webinar Anamnesi perfetta / Addizione Perfetta', 10447, 10443],
  [11346, 'Webinar Test per Forie / Anamnesi Perfetta', 10449, 10447],
  [11348, 'Webinar Addizione perfetta / Lenti Multifocali', 10443, 9284],
  [11350, 'Webinar Addizione perfetta / Lenti Progressive', 10443, 9375],
  [11352, 'Base Lampada a fessura / Lenti morbide', 10394, 10581],
  [11354, 'Base Topografia Corneale / Lenti morbide', 10379, 10581],
  [11356, 'Base Astigmatismo / Anamnesi Perfetta', 9110, 10447],
  [11358, 'Base Lampada a fessura / Topografia Corneale', 10394, 10379],
  [11362, 'Masterclass Dominanza oculare / Addizione Perfetta', 9096, 10443]
];

/* ---------- Stili ---------- */
var BLU = '#1FA2E0', NERO = '#0B0D12', AZZURRO = '#E3F4FC';

function intestazione_(sh, titoli, nota) {
  sh.clear();
  var r = 1;
  if (nota) {
    sh.getRange(1, 1).setValue(nota).setFontStyle('italic').setFontColor('#5B6573');
    r = 2;
  }
  sh.getRange(r, 1, 1, titoli.length).setValues([titoli])
    .setBackground(NERO).setFontColor('#FFFFFF').setFontWeight('bold').setWrap(true);
  sh.setFrozenRows(r);
  return r;
}

/* ---------- 1. Preparazione ---------- */
function preparaFoglio() {
  var ss = SpreadsheetApp.getActive();
  ss.setSpreadsheetTimeZone('Europe/Rome');

  var doc = ss.getSheetByName('Docenti') || ss.insertSheet('Docenti');
  if (doc.getLastRow() < 3) {
    var r = intestazione_(doc, ['ID prodotto', 'Corso', 'Prezzo pieno (€)', 'Docente', '% al docente'],
      'Un corso per riga. Cambia docente o percentuale qui e poi usa "Aggiorna adesso". I corsi nuovi vengono aggiunti da soli come "' + TITOLARE + '" con 0%: controllali.');
    doc.getRange(r + 1, 1, DOCENTI_INIZIALI.length, 5).setValues(DOCENTI_INIZIALI);
    doc.getRange(r + 1, 5, 200, 1).setNumberFormat('0%');
    doc.getRange(r + 1, 3, 200, 1).setNumberFormat('#,##0.00 €');
    doc.setColumnWidth(2, 360); doc.setColumnWidth(4, 180);
  }

  var pac = ss.getSheetByName('Pacchetti') || ss.insertSheet('Pacchetti');
  if (pac.getLastRow() < 3) {
    var r2 = intestazione_(pac, ['ID pacchetto', 'Pacchetto', 'ID corso 1', 'ID corso 2'],
      'Pacchetti con due corsi: l\'importo pagato viene diviso tra i due corsi in proporzione al loro prezzo pieno.');
    pac.getRange(r2 + 1, 1, PACCHETTI_INIZIALI.length, 4).setValues(PACCHETTI_INIZIALI);
    pac.setColumnWidth(2, 360);
  }

  var pag = ss.getSheetByName('Pagamenti') || ss.insertSheet('Pagamenti');
  if (pag.getLastRow() < 2) {
    intestazione_(pag, ['Data pagamento', 'Docente', 'Anno di riferimento', 'Importo pagato (€)', 'Note']);
    pag.getRange(2, 1, 500, 1).setNumberFormat('dd/mm/yyyy');
    pag.getRange(2, 4, 500, 1).setNumberFormat('#,##0.00 €');
    pag.setColumnWidth(2, 180); pag.setColumnWidth(5, 300);
  }

  ['Vendite', 'Compensi'].forEach(function (n) { if (!ss.getSheetByName(n)) ss.insertSheet(n); });
  ordinaSchede_();
  var s1 = ss.getSheetByName('Foglio1') || ss.getSheetByName('Sheet1');
  if (s1 && ss.getSheets().length > 1 && s1.getLastRow() === 0) ss.deleteSheet(s1);

  SpreadsheetApp.getUi().alert('Foglio pronto. Ora usa "2. Collega WooCommerce".');
}

function ordinaSchede_() {
  var ss = SpreadsheetApp.getActive();
  ['Compensi', 'Vendite', 'Pagamenti', 'Docenti', 'Pacchetti'].forEach(function (n, i) {
    var sh = ss.getSheetByName(n);
    if (sh) { ss.setActiveSheet(sh); ss.moveActiveSheet(i + 1); }
  });
}

/* ---------- 2. Collegamento ---------- */
function collegaWooCommerce() {
  var ui = SpreadsheetApp.getUi();
  var k = ui.prompt('Collega WooCommerce', 'Incolla la Consumer key (inizia con ck_):', ui.ButtonSet.OK_CANCEL);
  if (k.getSelectedButton() !== ui.Button.OK) return;
  var s = ui.prompt('Collega WooCommerce', 'Incolla la Consumer secret (inizia con cs_):', ui.ButtonSet.OK_CANCEL);
  if (s.getSelectedButton() !== ui.Button.OK) return;
  var props = PropertiesService.getScriptProperties();
  props.setProperty('WC_KEY', k.getResponseText().trim());
  props.setProperty('WC_SECRET', s.getResponseText().trim());
  try {
    scaricaPagina_(1, 1);
    ui.alert('Collegamento riuscito. Ora usa "3. Aggiorna adesso".');
  } catch (e) {
    ui.alert('Collegamento non riuscito: ' + e.message);
  }
}

function scaricaPagina_(pagina, perPagina) {
  var p = PropertiesService.getScriptProperties();
  var key = p.getProperty('WC_KEY'), sec = p.getProperty('WC_SECRET');
  if (!key || !sec) throw new Error('Chiave WooCommerce mancante: usa "2. Collega WooCommerce".');
  var url = SITO + '/wp-json/wc/v3/orders?status=completed&orderby=id&order=asc&per_page=' + perPagina +
    '&page=' + pagina + '&consumer_key=' + encodeURIComponent(key) + '&consumer_secret=' + encodeURIComponent(sec);
  var res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) {
    throw new Error('WooCommerce ha risposto ' + res.getResponseCode() + ': ' + res.getContentText().slice(0, 200));
  }
  var h = res.getHeaders();
  return { ordini: JSON.parse(res.getContentText()), pagine: Number(h['X-WP-TotalPages'] || h['x-wp-totalpages'] || 1) };
}

/* ---------- 3. Aggiornamento ---------- */
function aggiornaVendite() {
  var ss = SpreadsheetApp.getActive();
  var doc = ss.getSheetByName('Docenti'), pac = ss.getSheetByName('Pacchetti');
  if (!doc || !pac) throw new Error('Usa prima "1. Prepara il foglio".');

  // Mappe da Docenti e Pacchetti
  var dv = doc.getDataRange().getValues(), corsi = {}, primaRigaDoc = 0;
  for (var i = 0; i < dv.length; i++) {
    if (dv[i][0] === 'ID prodotto') { primaRigaDoc = i + 1; continue; }
    if (primaRigaDoc && dv[i][0] !== '') corsi[String(dv[i][0])] = { nome: dv[i][1], prezzo: Number(dv[i][2]) || 0, docente: dv[i][3] || TITOLARE, perc: Number(dv[i][4]) || 0 };
  }
  var pv = pac.getDataRange().getValues(), pacchetti = {}, inPac = false;
  for (var j = 0; j < pv.length; j++) {
    if (pv[j][0] === 'ID pacchetto') { inPac = true; continue; }
    if (inPac && pv[j][0] !== '') pacchetti[String(pv[j][0])] = [String(pv[j][2]), String(pv[j][3])];
  }

  // Scarica tutti gli ordini completati
  var ordini = [], prima = scaricaPagina_(1, 100);
  ordini = ordini.concat(prima.ordini);
  for (var pg = 2; pg <= prima.pagine; pg++) ordini = ordini.concat(scaricaPagina_(pg, 100).ordini);

  var righe = [], nuovi = [];
  ordini.forEach(function (o) {
    var totale = Number(o.total) || 0;
    var rimborsato = (o.refunds || []).reduce(function (s, r) { return s + Math.abs(Number(r.total) || 0); }, 0);
    var quotaValida = totale > 0 ? Math.max(0, (totale - rimborsato) / totale) : 0;
    var data = new Date(o.date_paid || o.date_created);
    (o.line_items || []).forEach(function (l) {
      var pagato = ((Number(l.total) || 0) + (Number(l.total_tax) || 0)) * quotaValida;
      if (pagato <= 0) return;
      var pid = String(l.product_id), parti;
      if (pacchetti[pid]) {
        var a = pacchetti[pid][0], b = pacchetti[pid][1];
        var pa = (corsi[a] || {}).prezzo || 1, pb = (corsi[b] || {}).prezzo || 1;
        parti = [[a, pagato * pa / (pa + pb), 'Dal pacchetto ' + l.name], [b, pagato * pb / (pa + pb), 'Dal pacchetto ' + l.name]];
      } else {
        parti = [[pid, pagato, rimborsato > 0 ? 'Rimborso parziale applicato' : '']];
      }
      parti.forEach(function (p) {
        var c = corsi[p[0]];
        if (!c) {
          c = { nome: l.name, prezzo: Number(l.price) || 0, docente: TITOLARE, perc: 0 };
          corsi[p[0]] = c;
          nuovi.push([Number(p[0]), l.name, c.prezzo, TITOLARE, 0]);
        }
        var importo = Math.round(p[1] * 100) / 100;
        var comp = Math.round(importo * c.perc * 100) / 100;
        righe.push([data, data.getFullYear(), o.number || o.id, c.nome, importo, c.docente, c.perc, comp, importo - comp, p[2]]);
      });
    });
  });
  righe.sort(function (x, y) { return y[0] - x[0]; });

  if (nuovi.length) {
    doc.getRange(doc.getLastRow() + 1, 1, nuovi.length, 5).setValues(nuovi).setBackground('#FFF4CC');
  }

  // Scheda Vendite
  var ven = ss.getSheetByName('Vendite');
  var r = intestazione_(ven, ['Data', 'Anno', 'Ordine n.', 'Corso', 'Pagato dal cliente (€)', 'Docente', '% al docente', 'Compenso docente (€)', 'Resta a Optometria Giovane (€)', 'Note'],
    'Si aggiorna da sola: non modificare a mano. Ultimo aggiornamento: ' + Utilities.formatDate(new Date(), 'Europe/Rome', 'dd/MM/yyyy HH:mm'));
  if (righe.length) {
    ven.getRange(r + 1, 1, righe.length, 10).setValues(righe);
    ven.getRange(r + 1, 1, righe.length, 1).setNumberFormat('dd/mm/yyyy');
    ven.getRange(r + 1, 5, righe.length, 1).setNumberFormat('#,##0.00 €');
    ven.getRange(r + 1, 7, righe.length, 1).setNumberFormat('0%');
    ven.getRange(r + 1, 8, righe.length, 2).setNumberFormat('#,##0.00 €');
  }
  ven.setColumnWidth(4, 340); ven.setColumnWidth(6, 170); ven.setColumnWidth(10, 260);

  scriviCompensi_(righe);
  if (nuovi.length) {
    try { SpreadsheetApp.getUi().alert('Ci sono ' + nuovi.length + ' corsi nuovi nella scheda Docenti (in giallo): controlla docente e percentuale, poi aggiorna di nuovo.'); } catch (e) {}
  }
}

/* ---------- Scheda Compensi ---------- */
function scriviCompensi_(righe) {
  var ss = SpreadsheetApp.getActive(), sh = ss.getSheetByName('Compensi');
  var coppie = {}, anni = {};
  righe.forEach(function (x) {
    if (x[6] > 0) { coppie[x[5] + '|' + x[1]] = [x[5], x[1]]; anni[x[1]] = true; }
  });
  var lista = Object.keys(coppie).map(function (k) { return coppie[k]; })
    .sort(function (a, b) { return b[1] - a[1] || String(a[0]).localeCompare(String(b[0])); });

  var r = intestazione_(sh, ['Anno', 'Docente', 'Corsi venduti', 'Venduto (€)', 'Compenso maturato (€)', 'Già pagato (€)', 'Da pagare (€)'],
    'Compensi per docente e per anno. Segna i pagamenti fatti nella scheda "Pagamenti" e "Da pagare" si aggiorna da solo.');
  var out = lista.map(function (c, i) {
    var row = r + 1 + i;
    var cond = 'Vendite!$F:$F,$B' + row + ',Vendite!$B:$B,$A' + row;
    return [c[1], c[0],
      '=COUNTIFS(' + cond + ')',
      '=SUMIFS(Vendite!$E:$E,' + cond + ')',
      '=SUMIFS(Vendite!$H:$H,' + cond + ')',
      '=SUMIFS(Pagamenti!$D:$D,Pagamenti!$B:$B,$B' + row + ',Pagamenti!$C:$C,$A' + row + ')',
      '=E' + row + '-F' + row];
  });
  if (out.length) {
    sh.getRange(r + 1, 1, out.length, 7).setValues(out);
    sh.getRange(r + 1, 4, out.length, 4).setNumberFormat('#,##0.00 €');
    sh.getRange(r + 1, 7, out.length, 1).setFontWeight('bold');
    // righe alterne per anno
    var anno = null, col = false;
    for (var i = 0; i < lista.length; i++) {
      if (lista[i][1] !== anno) { anno = lista[i][1]; col = !col; }
      sh.getRange(r + 1 + i, 1, 1, 7).setBackground(col ? AZZURRO : '#FFFFFF');
    }
  }
  sh.setColumnWidth(2, 190);
  sh.setColumnWidths(3, 5, 150);
}

/* ---------- 4. Aggiornamento automatico ---------- */
function attivaAggiornamentoAutomatico() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'aggiornaVendite') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('aggiornaVendite').timeBased().everyDays(1).atHour(3).inTimezone('Europe/Rome').create();
  SpreadsheetApp.getUi().alert('Fatto: il foglio si aggiorna da solo ogni notte verso le 3:00.');
}
