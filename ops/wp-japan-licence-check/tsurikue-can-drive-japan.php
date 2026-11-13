<?php
/**
 * Plugin Name: Tsurikue Japan Driving Licence Checker
 * Description: Read-only English travel document checklist displayed only by [tsurikue_can_drive_japan].
 * Version: 1.0.0
 *
 * Never decides legal eligibility. No personal data storage, cookies, or AJAX.
 */
if (!defined('ABSPATH')) { exit; }

function tsu_drive_checker_css() {
return <<<'CSS'
.tsu-drive{font-family:inherit;max-width:900px;margin:28px auto;color:#243941;line-height:1.65}
.tsu-drive *{box-sizing:border-box}
.tsu-drive a{color:#075d69;text-decoration:underline;text-underline-offset:2px}
.tsu-drive .hero{background:linear-gradient(125deg,#143949,#186678);color:#fff;padding:27px 25px;border-radius:16px 16px 0 0}
.tsu-drive .hero .eyebrow{font-size:.76rem;letter-spacing:.11em;text-transform:uppercase;font-weight:700;color:#b8e6e6}
.tsu-drive .hero h2{font-size:clamp(1.45rem,3vw,2rem);margin:8px 0;color:#fff;line-height:1.3}
.tsu-drive .hero p{margin:8px 0 0;color:#e7f5f4}
.tsu-drive .body{border:1px solid #d8e3e8;border-top:0;border-radius:0 0 16px 16px;padding:22px 22px 26px;background:#fff}
.tsu-drive .note{padding:12px 14px;background:#f1f6f7;border-left:3px solid #167386;color:#294451;font-size:.92rem;border-radius:0 8px 8px 0;margin:0 0 21px}
.tsu-drive .field{margin:0 0 21px}
.tsu-drive label{display:block;font-weight:750;margin:0 0 8px;color:#1e3744;font-size:1rem}
.tsu-drive .help{display:block;color:#5b6870;font-size:.86rem;margin:0 0 8px}
.tsu-drive select,.tsu-drive input[type=text]{display:block;width:100%;padding:12px 12px;border:1px solid #aebfc6;border-radius:9px;font:inherit;color:#172e36;background:#fff;min-height:48px}
.tsu-drive fieldset{border:1px solid #d8e3e8;border-radius:10px;padding:13px 15px 12px;margin:0 0 21px;min-width:0}
.tsu-drive legend{font-weight:750;color:#1e3744;padding:0 5px;font-size:1rem}
.tsu-drive .choice{display:flex;gap:10px;align-items:flex-start;line-height:1.4;font-weight:400;margin:10px 0;cursor:pointer;font-size:.94rem}
.tsu-drive input[type=radio]{accent-color:#146d74;width:18px;height:18px;flex:none;margin-top:2px}
.tsu-drive .two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.tsu-drive button{display:inline-flex;justify-content:center;align-items:center;min-height:48px;padding:12px 22px;background:#146d74;color:#fff;border:0;border-radius:9px;font:inherit;font-weight:800;cursor:pointer;box-shadow:none}
.tsu-drive button:hover{background:#0e505a}
.tsu-drive button:focus-visible,.tsu-drive a:focus-visible,.tsu-drive select:focus-visible,.tsu-drive input:focus-visible{outline:3px solid #df9d28;outline-offset:2px}
.tsu-drive .answer{display:none;margin-top:24px;padding:21px;border-radius:12px;background:#f2f6f7;border:1px solid #d7e3e7}
.tsu-drive .answer.show{display:block}
.tsu-drive .answer[data-tone=stop]{background:#fff6f2;border-color:#eebba7}
.tsu-drive .answer[data-tone=check]{background:#fffbed;border-color:#e8d28c}
.tsu-drive .answer h3{margin:0 0 10px;font-size:1.24rem;color:#1e3744}
.tsu-drive .answer p{margin:0 0 12px}
.tsu-drive .answer ol{margin:8px 0 14px;padding-left:1.35em}
.tsu-drive .answer li{margin-bottom:8px}
.tsu-drive .answer .tag{display:inline-block;margin:0 0 9px;border:1px solid #b9cfd1;background:#fff;border-radius:999px;padding:3px 9px;font-size:.76rem;font-weight:800}
.tsu-drive .answer .compare{margin:14px 0 0;padding:12px 14px;border-radius:8px;background:#fff;border:1px solid #cbdcdb}
.tsu-drive .compare a{display:inline-block;padding:9px 12px;border-radius:8px;background:#146d74;color:#fff;text-decoration:none;font-weight:800;min-height:44px}
.tsu-drive .compare small{display:block;color:#50616b;font-size:.78rem;margin-top:8px}
.tsu-drive .sources{margin-top:25px;padding-top:17px;border-top:1px solid #dbe6e8;font-size:.9rem}
.tsu-drive .sources p{margin:0 0 8px}
.tsu-drive .source-links{display:flex;flex-wrap:wrap;gap:8px 18px}
.tsu-drive .privacy{color:#586d75;font-size:.8rem;margin:14px 0 0}
.tsu-drive .destination{margin-top:20px;padding:15px;border-radius:10px;background:#f2f6f7}
.tsu-drive .destination h3{font-size:1.03rem;margin:0 0 6px}
.tsu-drive .destination p{margin:0 0 10px}
@media(max-width:600px){.tsu-drive .hero{padding:20px}.tsu-drive .body{padding:17px}.tsu-drive .two{grid-template-columns:1fr;gap:0}.tsu-drive button{width:100%}}
CSS;
}

function tsu_drive_checker_js() {
return <<<'JS'
(function () {
"use strict";
var eligibleTranslations = ["fr","de","be","ch","mc","tw"];
var sourceNpa = "https://www.npa.go.jp/english/bureau/traffic/r8_english.pdf.pdf";
var sourceJaf = "https://english.jaf.or.jp/driving-in-japan/drive-in-japan/switch-to-japanese-license";
var affiliate = "https://www.discovercars.com/?a_aid=tsurikue";
function isSpecial(code){ return eligibleTranslations.indexOf(code) !== -1; }

function decide(s) {
  var base = {
    tone:"check", title:"Check your documents before driving",
    summary:"This is a document guide, not an approval to drive or rent a car.",
    steps:[], compare:false
  };
  if (!s.country || !s.document || !s.valid || !s.reentry) {
    base.summary="Please complete all four questions first.";
    return base;
  }
  if (s.valid === "no") {
    return {tone:"stop",title:"Do not rely on expired documents",summary:"Your selected driving documents are not currently valid. Do not drive until you have a valid licence and all required documents.",steps:[
      "Renew or obtain a valid driving licence or permit as appropriate.",
      "Check your documents with the official authority and rental provider before travelling."
    ],compare:false};
  }
  var r;
  if (s.document === "japan") {
    if (s.country !== "jp") {
      r={tone:"check",title:"Check which licence you actually hold",summary:"You selected a Japanese driving licence, but a different issuing country. Please select Japan if your actual licence was issued by Japan.",steps:["Confirm the valid Japanese driving licence and vehicle category."],compare:false};
    } else {
      r={tone:"possible",title:"Japanese driving licence route",summary:"A valid Japanese driving licence is a recognised route to driving in Japan, within its licence class and validity period.",steps:[
        "Carry your valid Japanese driving licence.",
        "Check the vehicle class and rental-car company requirements."
      ],compare:true};
    }
  } else if (s.document === "geneva") {
    r={tone:"possible",title:"1949 Geneva Convention IDP: possible route",summary:"Japan recognises qualifying 1949 Geneva Convention International Driving Permits. Selecting this option does not prove your particular permit is accepted.",steps:[
      "Confirm that your IDP was issued by an authorised issuer of a contracting country/region and follows the prescribed 1949 Geneva format.",
      "Carry your valid original driving licence and original paper IDP; check permitted vehicle categories.",
      "Check the IDP's issue/expiry dates and the period since your landing in Japan."
    ],compare:true};
  } else if (s.document === "vienna") {
    r={tone:"stop",title:"A 1968 Vienna Convention IDP is not accepted",summary:"Japan does not accept a 1968 Vienna Convention IDP by itself for driving. Do not rely on this permit.",steps:[
      "Check whether you can obtain a qualifying 1949 Geneva Convention IDP from an authorised issuer.",
      isSpecial(s.country) ? "Alternatively, check the authorised Japanese-translation route available for licences issued in your selected region." : "A translation of most other foreign licences does not replace a qualifying 1949 IDP.",
      "Check the National Police Agency guidance before booking."
    ],compare:false};
  } else if (s.document === "translation") {
    if (isSpecial(s.country)) {
      r={tone:"possible",title:"Japanese translation route: possible",summary:"Licences issued in Switzerland, Germany, France, Belgium, Monaco and Taiwan may qualify when carried with an authorised Japanese translation.",steps:[
        "Carry your valid original licence and a Japanese translation made by an officially authorised body (not just any translator).",
        "Check the permitted vehicle class, validity and the time since entering Japan.",
        "Confirm the translation and required documents with the rental provider."
      ],compare:true};
    } else {
      r={tone:"stop",title:"A translation alone does not qualify here",summary:"The foreign-licence-plus-Japanese-translation visitor route is limited to six specified countries/regions. A translation from elsewhere is not itself permission to drive.",steps:[
        "Check whether a qualifying 1949 Geneva Convention IDP is available for your situation.",
        "If you live in Japan, ask the driver's licence centre about switching to a Japanese licence."
      ],compare:false};
    }
  } else if (s.document === "original") {
    if (s.country === "jp") {
      r={tone:"possible",title:"Valid Japanese licence may be enough",summary:"A valid Japanese driving licence is a recognised route for its authorised vehicle class.",steps:[
        "Carry the original valid licence and confirm rental-company requirements."
      ],compare:true};
    } else {
      r={tone:"stop",title:"A foreign licence alone is generally not enough",summary:"Most visitors need a qualifying 1949 Geneva IDP, or—if their licence comes from one of six specified regions—an authorised Japanese translation with the original licence.",steps:[
        isSpecial(s.country) ? "Check the official Japanese-translation route for your licence." : "Check the valid 1949 Geneva Convention IDP route with an authorised issuer.",
        "Do not drive until the required paperwork is confirmed."
      ],compare:false};
    }
  } else {
    r={tone:"check",title:"Identify the document route first",summary:"You may have a driving licence, but your route to driving in Japan is not confirmed.",steps:[
      "Find out whether your country/region issues a qualifying 1949 Geneva Convention IDP.",
      isSpecial(s.country) ? "Your selected issuing region may also use an authorised Japanese translation with the original licence." : "If that route is unavailable, check with the relevant driver's licence centre before planning to drive.",
      "Read the National Police Agency's rules below."
    ],compare:false};
  }
  if (s.valid === "unsure") {
    r.tone="check"; r.compare=false;
    r.steps.push("You were unsure of document validity. Check expiry and original-document requirements before relying on this route.");
  }
  if (s.reentry === "yes" && s.document !== "japan") {
    r.tone="check"; r.compare=false;
    r.steps.push("Important: for residents recorded in Japan's Basic Resident Register, leaving and re-entering within three months may NOT restart the one-year driving period. Ask the prefectural driver's licence centre.");
  } else if (s.reentry === "unsure" && s.document !== "japan") {
    r.tone="check"; r.compare=false;
    r.steps.push("If you live in Japan or have recently re-entered, confirm the one-year counting rule before driving.");
  }
  if (s.document !== "japan" && s.country !== "jp") {
    r.steps.push("For international permits or eligible foreign licences, the driving period is generally no longer than one year from landing, or until the relevant document expires, whichever comes first. Re-entry exceptions apply.");
  }
  r.steps.push("Final confirmation must come from the official rules and the rental company; age, insurance, vehicle class and required identification may also matter.");
  return r;
}

function link(url, text, sponsored) {
  var a=document.createElement("a");
  a.href=url;a.target="_blank";a.rel=sponsored?"sponsored nofollow noopener":"noopener noreferrer";
  a.textContent=text;return a;
}
function render(host, r) {
  var box=host.querySelector("[data-answer]");
  box.textContent="";
  box.dataset.tone=r.tone;
  var tag=document.createElement("span");tag.className="tag";tag.textContent="PRELIMINARY DOCUMENT GUIDANCE";
  box.appendChild(tag);
  var title=document.createElement("h3");title.textContent=r.title;box.appendChild(title);
  var summary=document.createElement("p");summary.textContent=r.summary;box.appendChild(summary);
  var list=document.createElement("ol");
  r.steps.forEach(function(step){var li=document.createElement("li");li.textContent=step;list.appendChild(li);});
  box.appendChild(list);
  var ref=document.createElement("p");ref.appendChild(link(sourceNpa,"Japan National Police Agency rules",false));
  ref.appendChild(document.createTextNode(" · "));
  ref.appendChild(link(sourceJaf,"JAF guidance",false));box.appendChild(ref);
  if(r.compare){
    var c=document.createElement("div");c.className="compare";
    var p=document.createElement("p");p.textContent="Planning a road trip beyond Hiroshima? After you confirm your legal driving eligibility, you can compare rental-car options.";c.appendChild(p);
    c.appendChild(link(affiliate,"Compare rental car options in Japan",true));
    var d=document.createElement("small");d.textContent="Affiliate disclosure: This link may earn me a commission if you make an eligible booking. This tool does not guarantee you can legally drive or rent a car.";c.appendChild(d);
    box.appendChild(c);
  }
  box.classList.add("show");
  box.scrollIntoView({behavior:"smooth",block:"nearest"});
}
function init(host){
  if(host.dataset.started==="1")return;
  host.dataset.started="1";
  var form=host.querySelector("form");
  var country=form.querySelector("[name=issuer]");
  var custom=form.querySelector("[data-other]");
  function adjustOther(){custom.hidden=country.value!=="other";}
  country.addEventListener("change",adjustOther);adjustOther();
  form.addEventListener("submit",function(event){
    event.preventDefault();
    var selected=form.querySelector("[name=documents]:checked");
    var validity=form.querySelector("[name=validity]:checked");
    var reentry=form.querySelector("[name=reentry]:checked");
    var s={country:country.value,document:selected?selected.value:"",valid:validity?validity.value:"",reentry:reentry?reentry.value:""};
    render(host,decide(s));
  });
}
window.tsurikueDriveDecide = decide; // Pure function exposed for regression tests.
document.addEventListener("DOMContentLoaded",function(){
  document.querySelectorAll("[data-tsurikue-drive-check]").forEach(init);
});
})();
JS;
}

function tsu_drive_checker_shortcode() {
return <<<'HTML'
<section class="tsu-drive" data-tsurikue-drive-check lang="en" aria-label="Driving in Japan licence document checker">
  <div class="hero">
    <div class="eyebrow">Tsurikue! · Japan travel helper</div>
    <h2>Can I Drive in Japan?</h2>
    <p>Check which driving documents you may need before planning a Japanese road trip. Takes about a minute.</p>
  </div>
  <div class="body">
    <p class="note"><strong>Important:</strong> This is a first-step document checklist—not a legal decision or permission to drive. Rules can differ by issuer, licence type, validity and date of entry. No personal information is sent or saved.</p>
    <form>
      <div class="field">
        <label for="tsu-issuer">1. Where was your driving licence issued?</label>
        <span class="help">Choose the issuing country or region, not your citizenship.</span>
        <select id="tsu-issuer" name="issuer" required>
          <option value="">Choose a country / region</option>
          <option value="us">United States</option>
          <option value="gb">United Kingdom</option>
          <option value="ca">Canada</option>
          <option value="au">Australia</option>
          <option value="nz">New Zealand</option>
          <option value="fr">France</option>
          <option value="de">Germany</option>
          <option value="ch">Switzerland</option>
          <option value="be">Belgium</option>
          <option value="mc">Monaco</option>
          <option value="tw">Taiwan</option>
          <option value="jp">Japan</option>
          <option value="kr">South Korea</option>
          <option value="cn">Mainland China</option>
          <option value="hk">Hong Kong</option>
          <option value="sg">Singapore</option>
          <option value="ph">Philippines</option>
          <option value="th">Thailand</option>
          <option value="my">Malaysia</option>
          <option value="id">Indonesia</option>
          <option value="vn">Vietnam</option>
          <option value="in">India</option>
          <option value="it">Italy</option>
          <option value="es">Spain</option>
          <option value="nl">Netherlands</option>
          <option value="se">Sweden</option>
          <option value="ae">United Arab Emirates</option>
          <option value="other">Other country / region</option>
        </select>
        <div data-other hidden><label for="tsu-other-country">Your country / region (for your own reference)</label>
          <input id="tsu-other-country" type="text" autocomplete="off" maxlength="80" placeholder="e.g. Brazil (not stored)"></div>
      </div>
      <fieldset>
        <legend>2. Which document route do you have?</legend>
        <label class="choice"><input type="radio" name="documents" value="japan" required> A valid Japanese driving licence</label>
        <label class="choice"><input type="radio" name="documents" value="geneva"> A 1949 Geneva Convention International Driving Permit (IDP)</label>
        <label class="choice"><input type="radio" name="documents" value="vienna"> A 1968 Vienna Convention IDP</label>
        <label class="choice"><input type="radio" name="documents" value="translation"> My foreign licence + an official Japanese translation</label>
        <label class="choice"><input type="radio" name="documents" value="original"> My original driving licence only</label>
        <label class="choice"><input type="radio" name="documents" value="unsure"> I'm not sure yet</label>
      </fieldset>
      <div class="two">
        <fieldset>
          <legend>3. Are your documents still valid?</legend>
          <label class="choice"><input type="radio" name="validity" value="yes" required> Yes</label>
          <label class="choice"><input type="radio" name="validity" value="no"> No / expired</label>
          <label class="choice"><input type="radio" name="validity" value="unsure"> Not sure</label>
        </fieldset>
        <fieldset>
          <legend>4. Are you registered as a resident of Japan and returning after a trip abroad lasting three months or less?</legend>
          <label class="choice"><input type="radio" name="reentry" value="no" required> No</label>
          <label class="choice"><input type="radio" name="reentry" value="yes"> Yes</label>
          <label class="choice"><input type="radio" name="reentry" value="unsure"> Not sure</label>
        </fieldset>
      </div>
      <button type="submit">Check my documents</button>
    </form>
    <div class="answer" data-answer role="status" aria-live="polite" aria-atomic="true"></div>
    <div class="sources">
      <p><strong>Official information to check before booking</strong></p>
      <div class="source-links">
        <a target="_blank" rel="noopener noreferrer" href="https://www.npa.go.jp/english/bureau/traffic/r8_english.pdf.pdf">National Police Agency (English)</a>
        <a target="_blank" rel="noopener noreferrer" href="https://english.jaf.or.jp/driving-in-japan/drive-in-japan/switch-to-japanese-license">JAF · Foreign licences and translations</a>
      </div>
      <p class="privacy">Checked against publicly available guidance on November 13, 2026. This page does not independently verify permit issuers, rental eligibility or changes made after that date.</p>
    </div>
    <div class="destination">
      <h3>Why explore western Japan by car?</h3>
      <p>City trams and trains are wonderful. But a car can open up extra stops along the Seto Inland Sea and San'in coast. Explore our <a href="https://tsurikue.com/en/">English Travel stories</a> for ideas—whether you decide to drive or not.</p>
    </div>
  </div>
</section>
HTML;
}

function tsu_drive_checker_assets() {
    if (!is_singular('post')) { return; }
    $post = get_queried_object();
    if (!($post instanceof WP_Post) || !has_shortcode($post->post_content, 'tsurikue_can_drive_japan')) { return; }
    wp_register_style('tsurikue-drive-checker', false, array(), '1.0.0');
    wp_enqueue_style('tsurikue-drive-checker');
    wp_add_inline_style('tsurikue-drive-checker', tsu_drive_checker_css());
    wp_register_script('tsurikue-drive-checker', false, array(), '1.0.0', true);
    wp_enqueue_script('tsurikue-drive-checker');
    wp_add_inline_script('tsurikue-drive-checker', tsu_drive_checker_js(), 'after');
}
add_action('wp_enqueue_scripts', 'tsu_drive_checker_assets', 20);
add_shortcode('tsurikue_can_drive_japan', 'tsu_drive_checker_shortcode');
