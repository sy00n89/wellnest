import { useState, useEffect, useRef } from "react";

// ── Google Fonts ──────────────────────────────────────────────────────────────
const FontLoader = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');
  `}</style>
);

// ── Design Tokens ─────────────────────────────────────────────────────────────
const T = {
  parchment: "#F7F4EF",
  parchmentDark: "#EDE9E1",
  surface: "#FFFFFF",
  sage: "#4A7C59",
  sageMid: "#6B9E7A",
  sageLight: "#C8DBC0",
  sagePale: "#EAF2E8",
  clay: "#C4845A",
  clayLight: "#F0D5C0",
  textPrimary: "#2C2C2C",
  textSecondary: "#7A7469",
  textMuted: "#A89F96",
  stressLow: "#7BC67E",
  stressMid: "#F4C55A",
  stressHigh: "#D9644A",
  border: "#E2DDD7",
  shadow: "0 2px 16px rgba(74,124,89,0.08)",
  shadowMd: "0 4px 32px rgba(74,124,89,0.12)",
};

// ── Global Styles ─────────────────────────────────────────────────────────────
const GlobalStyles = () => (
  <style>{`
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: ${T.parchment}; font-family: 'DM Sans', sans-serif; color: ${T.textPrimary}; display: flex; justify-content: center; }

    .wn-app { min-height: 100vh; background: ${T.parchment}; }

    .wn-page {
      width: 100%;
      max-width: 600px;
      margin: 0 auto;
      padding: 24px 20px 120px;
    }

    .wn-center {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 100%;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: ${T.sageLight}; border-radius: 4px; }

    /* Animations */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes breathe {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.03); }
    }
    @keyframes sway {
      0%, 100% { transform: rotate(-2deg); }
      50% { transform: rotate(2deg); }
    }
    @keyframes shimmer {
      0% { background-position: -200% center; }
      100% { background-position: 200% center; }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    @keyframes grow {
      from { transform: scale(0.8); opacity: 0; }
      to { transform: scale(1); opacity: 1; }
    }

    .fade-up { animation: fadeUp 0.5s ease forwards; }
    .fade-up-1 { animation: fadeUp 0.5s 0.1s ease both; }
    .fade-up-2 { animation: fadeUp 0.5s 0.2s ease both; }
    .fade-up-3 { animation: fadeUp 0.5s 0.3s ease both; }
    .fade-up-4 { animation: fadeUp 0.5s 0.4s ease both; }
    .fade-up-5 { animation: fadeUp 0.5s 0.5s ease both; }

    .plant-sway { animation: sway 4s ease-in-out infinite; transform-origin: bottom center; }
    .breathe { animation: breathe 3s ease-in-out infinite; }

    /* Tag pills */
    .tag { 
      display: inline-flex; align-items: center; gap: 6px;
      padding: 8px 14px; border-radius: 100px; font-size: 13px; font-weight: 500;
      border: 1.5px solid ${T.border}; background: ${T.surface};
      color: ${T.textSecondary}; cursor: pointer; transition: all 0.2s;
      font-family: 'DM Sans', sans-serif; line-height: 1;
    }
    .tag:hover { border-color: ${T.sageMid}; color: ${T.sage}; background: ${T.sagePale}; }
    .tag.active-green { border-color: ${T.sage}; background: ${T.sagePale}; color: ${T.sage}; }
    .tag.active-clay { border-color: ${T.clay}; background: ${T.clayLight}; color: ${T.clay}; }

    /* Stress bar */
    .stress-bar-fill {
      transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Nav */
    .nav-btn {
      display: flex; flex-direction: column; align-items: center; gap: 4px;
      padding: 8px 16px; border-radius: 12px; border: none; background: transparent;
      color: ${T.textMuted}; cursor: pointer; transition: all 0.2s; font-family: 'DM Sans', sans-serif;
    }
    .nav-btn.active { color: ${T.sage}; background: ${T.sagePale}; }
    .nav-btn span { font-size: 11px; font-weight: 500; }

    /* Card */
    .card {
      background: ${T.surface}; border-radius: 20px; padding: 24px;
      border: 1px solid ${T.border}; box-shadow: ${T.shadow};
    }
    .card-sm { padding: 16px; border-radius: 16px; }

    /* Button primary */
    .btn-primary {
      width: 100%; padding: 16px; background: ${T.sage}; color: white;
      border: none; border-radius: 14px; font-size: 16px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; font-family: 'DM Sans', sans-serif;
      letter-spacing: 0.01em;
    }
    .btn-primary:hover { background: #3d6b4b; transform: translateY(-1px); box-shadow: 0 6px 20px rgba(74,124,89,0.25); }
    .btn-primary:active { transform: translateY(0); }
    .btn-primary:disabled { background: ${T.textMuted}; cursor: not-allowed; transform: none; box-shadow: none; }

    /* Textarea / Input */
    .wn-input {
      width: 100%; padding: 14px 16px; border: 1.5px solid ${T.border};
      border-radius: 12px; font-family: 'DM Sans', sans-serif; font-size: 15px;
      color: ${T.textPrimary}; background: ${T.parchment}; outline: none;
      transition: border-color 0.2s; resize: none;
    }
    .wn-input:focus { border-color: ${T.sageMid}; background: white; }
    .wn-input::placeholder { color: ${T.textMuted}; }

    /* Loading shimmer */
    .shimmer {
      background: linear-gradient(90deg, ${T.parchment} 25%, ${T.parchmentDark} 50%, ${T.parchment} 75%);
      background-size: 200% auto;
      animation: shimmer 1.5s linear infinite;
    }
  `}</style>
);

// ── Helpers ───────────────────────────────────────────────────────────────────
const today = () => new Date().toISOString().split("T")[0];

const greet = () => {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
};

const formatDate = (d) =>
  new Date(d + "T12:00:00").toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric",
  });

const stressColor = (n) => {
  if (n <= 3) return T.stressLow;
  if (n <= 6) return T.stressMid;
  return T.stressHigh;
};

// ── Mock Data ─────────────────────────────────────────────────────────────────
const MOCK_ENTRIES = [
  { id: "1", date: (() => { const d=new Date(); d.setDate(d.getDate()-0); return d.toISOString().split("T")[0]; })(), time: "21:15", mood: "stressed", stress_level: 7, triggers: ["Work deadline"], physical_signs: ["Neck tension", "Headache"], notes: "Big presentation tomorrow." },
  { id: "2", date: (() => { const d=new Date(); d.setDate(d.getDate()-1); return d.toISOString().split("T")[0]; })(), time: "20:00", mood: "anxious", stress_level: 6, triggers: ["Sleep deprivation"], physical_signs: ["Fatigue"], notes: "" },
  { id: "3", date: (() => { const d=new Date(); d.setDate(d.getDate()-2); return d.toISOString().split("T")[0]; })(), time: "19:30", mood: "neutral", stress_level: 4, triggers: [], physical_signs: [], notes: "Quiet day." },
  { id: "4", date: (() => { const d=new Date(); d.setDate(d.getDate()-3); return d.toISOString().split("T")[0]; })(), time: "22:00", mood: "overwhelmed", stress_level: 9, triggers: ["Work deadline", "Relationship"], physical_signs: ["Neck tension", "Restlessness", "Headache"], notes: "Everything hit at once." },
  { id: "5", date: (() => { const d=new Date(); d.setDate(d.getDate()-4); return d.toISOString().split("T")[0]; })(), time: "18:45", mood: "calm", stress_level: 2, triggers: [], physical_signs: [], notes: "Good walk in the evening." },
  { id: "6", date: (() => { const d=new Date(); d.setDate(d.getDate()-5); return d.toISOString().split("T")[0]; })(), time: "20:30", mood: "worried", stress_level: 5, triggers: ["Financial"], physical_signs: ["Fatigue"], notes: "" },
  { id: "7", date: (() => { const d=new Date(); d.setDate(d.getDate()-6); return d.toISOString().split("T")[0]; })(), time: "21:00", mood: "anxious", stress_level: 7, triggers: ["Work deadline", "Sleep deprivation"], physical_signs: ["Headache", "Fatigue"], notes: "Monday always feels heavy." },
];

const MOCK_INSIGHT = `Over the past week, your stress has tended to peak in the evenings — particularly around work deadlines, which appeared in four of your seven entries. Your body has been signaling this pattern through recurring neck tension and headaches, often together.

Two days stand out as genuinely lighter — Wednesday and Saturday, when you had no active triggers and your stress sat below 4. On both days you noted feeling settled and present.

The beginning of your week tends to carry more weight than the end. This is useful information: Monday and Tuesday may benefit from a little extra gentleness in how you pace yourself.`;

const MOCK_PLANT = { stage: "seedling", check_ins: 7, days_active: 12 };

// ── Plant Illustrations ───────────────────────────────────────────────────────
const PlantSVG = ({ stage, size = 120 }) => {
  const plants = {
    sprout: (
      <svg width={size} height={size} viewBox="0 0 120 120">
        <ellipse cx="60" cy="108" rx="28" ry="8" fill={T.sageLight} opacity="0.5"/>
        <line x1="60" y1="108" x2="60" y2="72" stroke={T.sage} strokeWidth="3" strokeLinecap="round"/>
        <path d="M60 80 Q48 68 52 58 Q62 64 60 80" fill={T.sageMid} opacity="0.85"/>
        <path d="M60 74 Q72 64 70 54 Q60 60 60 74" fill={T.sage} opacity="0.9"/>
      </svg>
    ),
    seedling: (
      <svg width={size} height={size} viewBox="0 0 120 120">
        <ellipse cx="60" cy="110" rx="32" ry="9" fill={T.sageLight} opacity="0.4"/>
        <line x1="60" y1="110" x2="60" y2="60" stroke={T.sage} strokeWidth="3.5" strokeLinecap="round"/>
        <path d="M60 88 Q42 72 46 56 Q62 64 60 88" fill={T.sageMid}/>
        <path d="M60 78 Q78 62 76 48 Q60 56 60 78" fill={T.sage}/>
        <path d="M60 96 Q52 86 54 78" stroke={T.sageMid} strokeWidth="2" fill="none" strokeLinecap="round"/>
        <circle cx="60" cy="60" r="10" fill={T.sageLight} opacity="0.6"/>
        <path d="M54 60 Q60 52 66 60 Q60 68 54 60" fill={T.sage}/>
      </svg>
    ),
    plant: (
      <svg width={size} height={size} viewBox="0 0 120 120">
        <ellipse cx="60" cy="112" rx="36" ry="10" fill={T.sageLight} opacity="0.35"/>
        <line x1="60" y1="112" x2="60" y2="50" stroke={T.sage} strokeWidth="4" strokeLinecap="round"/>
        <path d="M60 95 Q36 76 40 54 Q64 64 60 95" fill={T.sageMid}/>
        <path d="M60 80 Q84 62 82 42 Q60 52 60 80" fill={T.sage}/>
        <path d="M60 65 Q44 54 46 40 Q62 48 60 65" fill={T.sageLight} opacity="0.9"/>
        <ellipse cx="60" cy="46" rx="14" ry="18" fill={T.sage} opacity="0.9"/>
        <ellipse cx="60" cy="44" rx="10" ry="14" fill={T.sageMid}/>
      </svg>
    ),
    young_tree: (
      <svg width={size} height={size} viewBox="0 0 120 120">
        <ellipse cx="60" cy="114" rx="40" ry="10" fill={T.sageLight} opacity="0.3"/>
        <rect x="55" y="70" width="10" height="44" rx="5" fill="#8B6340"/>
        <ellipse cx="60" cy="58" rx="28" ry="34" fill={T.sage} opacity="0.9"/>
        <ellipse cx="44" cy="68" rx="18" ry="22" fill={T.sageMid} opacity="0.8"/>
        <ellipse cx="76" cy="66" rx="18" ry="22" fill={T.sageMid} opacity="0.8"/>
        <ellipse cx="60" cy="48" rx="22" ry="26" fill={T.sage}/>
      </svg>
    ),
    mature_tree: (
      <svg width={size} height={size} viewBox="0 0 120 120">
        <ellipse cx="60" cy="116" rx="44" ry="10" fill={T.sageLight} opacity="0.25"/>
        <rect x="54" y="72" width="12" height="44" rx="6" fill="#8B6340"/>
        <ellipse cx="60" cy="55" rx="36" ry="40" fill={T.sage} opacity="0.85"/>
        <ellipse cx="38" cy="68" rx="24" ry="28" fill={T.sageMid} opacity="0.75"/>
        <ellipse cx="82" cy="66" rx="24" ry="28" fill={T.sageMid} opacity="0.75"/>
        <ellipse cx="60" cy="42" rx="28" ry="32" fill={T.sage}/>
        <ellipse cx="60" cy="36" rx="20" ry="22" fill={T.sageMid} opacity="0.8"/>
      </svg>
    ),
  };
  return plants[stage] || plants.sprout;
};

// ── Welcome Screen ────────────────────────────────────────────────────────────
const WelcomeScreen = ({ onBegin }) => (
  <div style={{
    minHeight: "100vh", width: "100vw", display: "flex", flexDirection: "column",
    alignItems: "center", justifyContent: "center", padding: "40px 24px",
    background: `linear-gradient(160deg, ${T.sagePale} 0%, ${T.parchment} 50%, ${T.clayLight} 100%)`,
  }}>
    <div className="fade-up-1" style={{ marginBottom: 40 }}>
      <div className="plant-sway" style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
        <PlantSVG stage="seedling" size={140} />
      </div>
    </div>

    <div className="fade-up-2" style={{ textAlign: "center", marginBottom: 16 }}>
      <h1 style={{ fontFamily: "Lora, serif", fontSize: 42, fontWeight: 600, color: T.sage, letterSpacing: "-0.5px" }}>
        Wellnest
      </h1>
    </div>

    <div className="fade-up-3" style={{ textAlign: "center", maxWidth: 320, marginBottom: 56 }}>
      <p style={{ fontFamily: "Lora, serif", fontStyle: "italic", fontSize: 18, color: T.textSecondary, lineHeight: 1.6 }}>
        A place to notice<br />how you're feeling.
      </p>
    </div>

    <div className="fade-up-4" style={{ width: "100%", maxWidth: 320 }}>
      <button className="btn-primary" onClick={onBegin} style={{ fontSize: 17, letterSpacing: "0.02em" }}>
        Begin
      </button>
    </div>

    <div className="fade-up-5" style={{ marginTop: 40, textAlign: "center" }}>
      <p style={{ fontSize: 12, color: T.textMuted, lineHeight: 1.8 }}>
        No account needed · Your data, your story
      </p>
    </div>
  </div>
);

// ── Check-In Screen ───────────────────────────────────────────────────────────
const MOODS = [
  { value: "calm", label: "Calm", emoji: "😌" },
  { value: "peaceful", label: "Peaceful", emoji: "🌿" },
  { value: "neutral", label: "Neutral", emoji: "😐" },
  { value: "worried", label: "Worried", emoji: "😟" },
  { value: "anxious", label: "Anxious", emoji: "😰" },
  { value: "stressed", label: "Stressed", emoji: "😣" },
  { value: "angry", label: "Angry", emoji: "😠" },
  { value: "overwhelmed", label: "Overwhelmed", emoji: "🌊" },
];

const PHYSICAL_SIGNS = ["Neck tension", "Headache", "Facial tightness", "Fatigue", "Restlessness", "Appetite changes", "Dizziness", "Chest tightness"];
const TRIGGERS = ["Work deadline", "Relationship", "Sleep deprivation", "Social pressure", "Health concern", "Financial", "School / Studies", "Uncertainty"];

const CheckInScreen = ({ onSubmit }) => {
  const [stress, setStress] = useState(5);
  const [mood, setMood] = useState(null);
  const [signs, setSigns] = useState([]);
  const [triggers, setTriggers] = useState([]);
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const toggleArr = (arr, setArr, val) =>
    setArr(prev => prev.includes(val) ? prev.filter(v => v !== val) : [...prev, val]);

  const handleSubmit = async () => {
    if (!mood) return;
    setSaving(true);
    await new Promise(r => setTimeout(r, 800));
    onSubmit({ id: Date.now().toString(), date: today(), time: new Date().toTimeString().slice(0, 8), mood, stress_level: stress, triggers, physical_signs: signs, notes });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
    setMood(null); setStress(5); setSigns([]); setTriggers([]); setNotes("");
  };

  return (
    <div className="wn-page">
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 32 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: T.textMuted, marginBottom: 4 }}>
          {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </p>
        <h2 style={{ fontFamily: "Lora, serif", fontSize: 28, fontWeight: 600, color: T.textPrimary }}>
          {greet()}
        </h2>
        <p style={{ fontSize: 15, color: T.textSecondary, marginTop: 4 }}>How are you right now?</p>
      </div>

      {saved && (
        <div className="fade-up card" style={{ background: T.sagePale, border: `1px solid ${T.sageLight}`, marginBottom: 20, textAlign: "center" }}>
          <p style={{ color: T.sage, fontWeight: 600 }}>✓ Noted. You showed up today.</p>
        </div>
      )}

      {/* Stress Level */}
      <div className="card fade-up-1" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Stress level
          </h3>
          <span style={{ fontFamily: "Lora, serif", fontSize: 36, fontWeight: 600, color: stressColor(stress) }}>
            {stress}
          </span>
        </div>

        {/* Number selector */}
        <div style={{ display: "flex", gap: 6, justifyContent: "space-between", marginBottom: 12 }}>
          {[1,2,3,4,5,6,7,8,9,10].map(n => (
            <button key={n} onClick={() => setStress(n)} style={{
              flex: 1, aspectRatio: "1", borderRadius: 10, border: "1.5px solid",
              borderColor: stress === n ? stressColor(n) : T.border,
              background: stress === n ? stressColor(n) : T.parchment,
              color: stress === n ? "white" : n <= stress ? stressColor(n) : T.textMuted,
              fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.15s",
              fontFamily: "DM Sans, sans-serif",
            }}>
              {n}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: 12, color: T.textMuted }}>Settled</span>
          <span style={{ fontSize: 12, color: T.textMuted }}>Overwhelmed</span>
        </div>
      </div>

      {/* Mood */}
      <div className="card fade-up-2" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }}>
          Mood
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {MOODS.map(m => (
            <button key={m.value} onClick={() => setMood(m.value)} style={{
              padding: "12px 6px", borderRadius: 12, border: "1.5px solid",
              borderColor: mood === m.value ? T.sage : T.border,
              background: mood === m.value ? T.sagePale : T.parchment,
              cursor: "pointer", transition: "all 0.15s", textAlign: "center",
            }}>
              <div style={{ fontSize: 22, marginBottom: 4 }}>{m.emoji}</div>
              <div style={{ fontSize: 11, fontWeight: 500, color: mood === m.value ? T.sage : T.textSecondary, fontFamily: "DM Sans, sans-serif" }}>
                {m.label}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Physical Signs */}
      <div className="card fade-up-3" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
          Physical signs
        </h3>
        <p style={{ fontSize: 13, color: T.textMuted, marginBottom: 16 }}>What is your body telling you?</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {PHYSICAL_SIGNS.map(s => (
            <button key={s} className={`tag ${signs.includes(s) ? "active-green" : ""}`}
              onClick={() => toggleArr(signs, setSigns, s)}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Triggers */}
      <div className="card fade-up-4" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }}>
          Triggers
        </h3>
        <p style={{ fontSize: 13, color: T.textMuted, marginBottom: 16 }}>What seems to have contributed?</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {TRIGGERS.map(t => (
            <button key={t} className={`tag ${triggers.includes(t) ? "active-clay" : ""}`}
              onClick={() => toggleArr(triggers, setTriggers, t)}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div className="card fade-up-5" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
          Reflection
        </h3>
        <textarea
          className="wn-input"
          rows={4}
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="Anything else on your mind? (optional)"
        />
      </div>

      <button className="btn-primary" onClick={handleSubmit} disabled={!mood || saving}>
        {saving ? "Saving..." : "Save check-in"}
      </button>
    </div>
  );
};

// ── Insights Screen ───────────────────────────────────────────────────────────
const InsightsScreen = ({ entries }) => {
  const [insightLoading, setInsightLoading] = useState(false);
  const [insight, setInsight] = useState("");
  const [insightGenerated, setInsightGenerated] = useState(false);

  const generateInsight = async () => {
    setInsightLoading(true);
    setInsight("");

    try {
      // Build a structured summary of the user's recent entries
      const recentEntries = entries.slice(0, 14);

      const entrySummary = recentEntries.map(e =>
        `Date: ${e.date}, Time: ${e.time?.slice(0,5)}, Mood: ${e.mood}, Stress: ${e.stress_level}/10, Triggers: ${(e.triggers||[]).join(", ")||"none"}, Physical signs: ${(e.physical_signs||[]).join(", ")||"none"}, Notes: ${e.notes||"none"}`
      ).join("\n");

      const prompt = `You are a warm, thoughtful wellness companion grounded in stress science. A user has been tracking their stress and wellbeing. Here are their recent check-in entries:\n\n${entrySummary}\n\nBased on these entries, write a structured insight report with exactly 5 sections. Each section must start with its label on its own line, followed by 2-3 sentences of content. Use this exact format:\n\nWHAT YOUR BODY IS SAYING\n[2-3 sentences about physical signs and what they signal. Grounded in Allostatic Load — the body accumulates stress before the mind recognizes it.]\n\nWHAT'S DRIVING IT\n[2-3 sentences identifying the key triggers and patterns. Grounded in Perceived Stress Theory — stress is shaped by what we perceive as threatening or uncontrollable.]\n\nHOW YOU'RE INTERPRETING IT\n[2-3 sentences on whether the user seems to be appraising situations as threats or challenges. Grounded in Cognitive Appraisal Theory by Lazarus and Folkman.]\n\nA MOMENT THAT HELPED\n[2-3 sentences identifying any lighter or calmer moments and what seemed to make them possible. Grounded in Behavioral Activation — certain behaviors buffer stress.]\n\nONE THING WORTH NOTICING\n[1-2 sentences. A single gentle observation the user can carry with them. Not advice — just awareness.]\n\nRules: Do not use markdown headers, bullet points, or asterisks. Do not give medical advice or diagnoses. Do not use the word streak. Write in plain warm sentences. Keep each section short and easy to read.`;

      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": import.meta.env.VITE_ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
          "anthropic-dangerous-direct-browser-access": "true",
        },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const data = await response.json();
      const text = data.content?.[0]?.text || "Unable to generate insight right now. Please try again.";

      // Parse into sections
      const sectionLabels = ["WHAT YOUR BODY IS SAYING", "WHAT'S DRIVING IT", "HOW YOU'RE INTERPRETING IT", "A MOMENT THAT HELPED", "ONE THING WORTH NOTICING"];
      const sectionIcons = ["🫁", "🔍", "💭", "🌤️", "✦"];
      const sectionColors = [T.clay, T.sage, T.sageMid, T.stressLow, T.textSecondary];

      const parsed = sectionLabels.map((label, i) => {
        const regex = new RegExp(`${label}\\s*\\n([\\s\\S]*?)(?=${sectionLabels.slice(i+1).map(l => l.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')}|$)`, 'i');
        const match = text.match(regex);
        return { label, icon: sectionIcons[i], color: sectionColors[i], content: match ? match[1].trim() : "" };
      }).filter(s => s.content);

      setInsight(parsed.length > 0 ? parsed : text);
    } catch (err) {
      console.error("Insight error:", err);
      setInsight("Something went wrong generating your insight. Please try again.");
    }

    setInsightLoading(false);
    setInsightGenerated(true);
  };

  // Weekly stress data
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toISOString().split("T")[0];
  });

  const weeklyData = weekDays.map(date => {
    const dayEntries = entries.filter(e => e.date === date);
    const avg = dayEntries.length ? Math.round(dayEntries.reduce((s, e) => s + e.stress_level, 0) / dayEntries.length) : null;
    return { date, avg, label: new Date(date + "T12:00:00").toLocaleDateString("en-US", { weekday: "short" }) };
  });

  // Top triggers
  const triggerCounts = {};
  entries.forEach(e => (e.triggers || []).forEach(t => { triggerCounts[t] = (triggerCounts[t] || 0) + 1; }));
  const topTriggers = Object.entries(triggerCounts).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const maxCount = topTriggers[0]?.[1] || 1;

  // Top physical signs
  const signCounts = {};
  entries.forEach(e => (e.physical_signs || []).forEach(s => { signCounts[s] = (signCounts[s] || 0) + 1; }));
  const topSigns = Object.entries(signCounts).sort((a, b) => b[1] - a[1]).slice(0, 4);

  return (
    <div className="wn-page">
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h2 style={{ fontFamily: "Lora, serif", fontSize: 28, fontWeight: 600, color: T.textPrimary }}>Insights</h2>
        <p style={{ fontSize: 14, color: T.textSecondary, marginTop: 4 }}>Patterns from your last 7 days</p>
      </div>

      {/* AI Narrative */}
      <div className="card fade-up-1" style={{ marginBottom: 16, borderLeft: `4px solid ${T.sage}` }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 16 }}>🌿</span>
            <h3 style={{ fontSize: 14, fontWeight: 600, color: T.sage, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Your Pattern
            </h3>
          </div>
          <button onClick={generateInsight} disabled={insightLoading} style={{
            padding: "6px 12px", border: `1px solid ${T.sageLight}`, borderRadius: 8,
            background: "transparent", color: T.sage, fontSize: 12, fontWeight: 500,
            cursor: "pointer", fontFamily: "DM Sans, sans-serif",
          }}>
            {insightLoading ? "Reading..." : "Refresh"}
          </button>
        </div>

        {insightLoading ? (
          <div>
            {[100, 85, 92, 60, 75].map((w, i) => (
              <div key={i} className="shimmer" style={{ height: 14, borderRadius: 7, marginBottom: 10, width: `${w}%` }} />
            ))}
          </div>
        ) : insight ? (
          <div>
            {Array.isArray(insight) ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {insight.map((section, i) => (
                  <div key={i} style={{ borderLeft: `3px solid ${section.color}`, paddingLeft: 14 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                      <span style={{ fontSize: 13 }}>{section.icon}</span>
                      <p style={{ fontSize: 11, fontWeight: 700, color: section.color, textTransform: "uppercase", letterSpacing: "0.1em" }}>
                        {section.label}
                      </p>
                    </div>
                    <p style={{ fontSize: 14, color: T.textPrimary, lineHeight: 1.75 }}>
                      {section.content}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div>
                {insight.split("\n\n").map((para, i) => (
                  <p key={i} style={{ fontSize: 15, color: T.textPrimary, lineHeight: 1.75, marginBottom: 14 }}>
                    {para}
                  </p>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "16px 0" }}>
            <p style={{ color: T.textMuted, fontSize: 14, marginBottom: 12 }}>
              Generate a plain-language summary of your patterns.
            </p>
            <button onClick={generateInsight} style={{
              padding: "10px 20px", background: T.sage, color: "white", border: "none",
              borderRadius: 10, fontWeight: 600, cursor: "pointer", fontFamily: "DM Sans, sans-serif",
            }}>
              Generate insight
            </button>
          </div>
        )}

        {insightGenerated && !insightLoading && (
          <p style={{ fontSize: 11, color: T.textMuted, marginTop: 16, fontStyle: "italic" }}>
            Based on your recent entries · AI-assisted · Not clinical advice
          </p>
        )}
      </div>

      {/* Weekly Stress */}
      <div className="card fade-up-2" style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 20 }}>
          7-Day Stress
        </h3>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 80 }}>
          {weeklyData.map(({ date, avg, label }) => (
            <div key={date} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <div style={{ width: "100%", borderRadius: 6, backgroundColor: avg ? stressColor(avg) : T.parchmentDark, height: avg ? `${(avg / 10) * 72}px` : "4px", transition: "height 0.4s ease", opacity: avg ? 1 : 0.4 }} />
              <span style={{ fontSize: 11, color: T.textMuted, fontWeight: 500 }}>{label}</span>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
          <span style={{ fontSize: 11, color: T.textMuted }}>Lower stress</span>
          <span style={{ fontSize: 11, color: T.textMuted }}>Higher stress</span>
        </div>
      </div>

      {/* Top Triggers */}
      {topTriggers.length > 0 && (
        <div className="card fade-up-3" style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 20 }}>
            Common Triggers
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {topTriggers.map(([trigger, count]) => (
              <div key={trigger}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 14, color: T.textPrimary, fontWeight: 500 }}>{trigger}</span>
                  <span style={{ fontSize: 13, color: T.clay, fontWeight: 600 }}>{count}×</span>
                </div>
                <div style={{ height: 6, borderRadius: 3, background: T.parchmentDark, overflow: "hidden" }}>
                  <div className="stress-bar-fill" style={{ height: "100%", borderRadius: 3, background: T.clay, width: `${(count / maxCount) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Physical Signs */}
      {topSigns.length > 0 && (
        <div className="card fade-up-4" style={{ marginBottom: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: T.textSecondary, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }}>
            Body Signals
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {topSigns.map(([sign, count]) => (
              <div key={sign} style={{
                padding: "8px 14px", borderRadius: 100, background: T.sagePale,
                border: `1px solid ${T.sageLight}`, display: "flex", alignItems: "center", gap: 8,
              }}>
                <span style={{ fontSize: 13, color: T.sage, fontWeight: 500 }}>{sign}</span>
                <span style={{ fontSize: 11, color: T.sageMid, fontWeight: 600, background: T.sageLight, borderRadius: 100, padding: "1px 7px" }}>{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Share with clinician */}
      <div className="card fade-up-5" style={{ background: T.parchmentDark, border: "none", textAlign: "center" }}>
        <p style={{ fontFamily: "Lora, serif", fontStyle: "italic", fontSize: 15, color: T.textSecondary, marginBottom: 14 }}>
          Working with a therapist or doctor?
        </p>
        <button style={{
          padding: "10px 24px", border: `1.5px solid ${T.sage}`, borderRadius: 10,
          background: "transparent", color: T.sage, fontSize: 14, fontWeight: 600,
          cursor: "pointer", fontFamily: "DM Sans, sans-serif",
        }}>
          Export report for care provider →
        </button>
        <p style={{ fontSize: 11, color: T.textMuted, marginTop: 10 }}>
          Coming soon — a clean PDF summary of your patterns
        </p>
      </div>
    </div>
  );
};

// ── History Screen ────────────────────────────────────────────────────────────
const moodColor = {
  calm: T.stressLow, peaceful: T.stressLow, neutral: T.stressMid,
  worried: "#E8A85A", anxious: T.stressHigh, stressed: T.stressHigh,
  angry: "#D9644A", overwhelmed: "#C4505A",
};

const HistoryScreen = ({ entries, onDelete }) => {
  const [filter, setFilter] = useState("");

  const filtered = entries
    .filter(e => !filter || e.date >= filter)
    .sort((a, b) => b.date.localeCompare(a.date) || b.time.localeCompare(a.time));

  return (
    <div className="wn-page">
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h2 style={{ fontFamily: "Lora, serif", fontSize: 28, fontWeight: 600, color: T.textPrimary }}>History</h2>
        <p style={{ fontSize: 14, color: T.textSecondary, marginTop: 4 }}>{entries.length} entries logged</p>
      </div>

      {filtered.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <p style={{ color: T.textMuted, fontFamily: "Lora, serif", fontStyle: "italic" }}>
            No entries yet.<br />Your story begins with a single check-in.
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {filtered.map((entry, i) => (
            <div key={entry.id} className="card fade-up" style={{
              animationDelay: `${i * 0.05}s`,
              borderLeft: `4px solid ${stressColor(entry.stress_level)}`,
              padding: "18px 20px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <p style={{ fontSize: 13, color: T.textMuted, marginBottom: 2 }}>
                    {formatDate(entry.date)} · {entry.time?.slice(0, 5)}
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{
                      fontSize: 12, fontWeight: 600, padding: "3px 10px", borderRadius: 100,
                      background: moodColor[entry.mood] + "22", color: moodColor[entry.mood],
                      textTransform: "capitalize",
                    }}>
                      {entry.mood}
                    </span>
                    <span style={{ fontFamily: "Lora, serif", fontSize: 22, fontWeight: 600, color: stressColor(entry.stress_level) }}>
                      {entry.stress_level}
                    </span>
                  </div>
                </div>
                <button onClick={() => onDelete(entry.id)} style={{
                  background: "none", border: "none", color: T.textMuted, cursor: "pointer",
                  fontSize: 16, padding: 4, opacity: 0.6, transition: "opacity 0.2s",
                }}>
                  ✕
                </button>
              </div>

              {(entry.triggers?.length > 0 || entry.physical_signs?.length > 0) && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: entry.notes ? 10 : 0 }}>
                  {(entry.triggers || []).map(t => (
                    <span key={t} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 100, background: T.clayLight, color: T.clay }}>{t}</span>
                  ))}
                  {(entry.physical_signs || []).map(s => (
                    <span key={s} style={{ fontSize: 11, padding: "3px 10px", borderRadius: 100, background: T.sagePale, color: T.sage }}>{s}</span>
                  ))}
                </div>
              )}

              {entry.notes && (
                <p style={{ fontSize: 13, color: T.textSecondary, fontStyle: "italic", lineHeight: 1.6 }}>
                  "{entry.notes}"
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── Plant Screen ──────────────────────────────────────────────────────────────
const PLANT_STAGES = ["sprout", "seedling", "plant", "young_tree", "mature_tree"];
const STAGE_NAMES = { sprout: "Sprout", seedling: "Seedling", plant: "Young Plant", young_tree: "Young Tree", mature_tree: "Mature Tree" };
const STAGE_DESC = {
  sprout: "Just beginning. Every check-in is a moment of care.",
  seedling: "Taking root. You're building awareness, one day at a time.",
  plant: "Growing steadily. Your pattern recognition is deepening.",
  young_tree: "Standing tall. You're learning what your body and mind need.",
  mature_tree: "A full presence. You carry self-knowledge that is yours alone.",
};

const PlantScreen = ({ plantData, entries }) => {
  const stage = plantData?.stage || "sprout";
  const stageIdx = PLANT_STAGES.indexOf(stage);
  const checkIns = entries.length;
  const daysActive = plantData?.days_active || checkIns;

  return (
    <div className="wn-page">
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h2 style={{ fontFamily: "Lora, serif", fontSize: 28, fontWeight: 600, color: T.textPrimary }}>Your Plant</h2>
        <p style={{ fontSize: 14, color: T.textSecondary, marginTop: 4 }}>A living reflection of your practice</p>
      </div>

      {/* Plant Hero */}
      <div className="card fade-up-1" style={{
        textAlign: "center", padding: "40px 24px 32px",
        background: `linear-gradient(160deg, ${T.sagePale} 0%, ${T.parchment} 100%)`,
        marginBottom: 16,
      }}>
        <div className="plant-sway" style={{ display: "inline-block", marginBottom: 24 }}>
          <PlantSVG stage={stage} size={160} />
        </div>
        <h3 style={{ fontFamily: "Lora, serif", fontSize: 26, fontWeight: 600, color: T.sage, marginBottom: 8 }}>
          {STAGE_NAMES[stage]}
        </h3>
        <p style={{ fontSize: 15, color: T.textSecondary, lineHeight: 1.7, maxWidth: 280, margin: "0 auto 24px" }}>
          {STAGE_DESC[stage]}
        </p>

        {/* Stage progress */}
        <div style={{ display: "flex", justifyContent: "center", gap: 8, marginBottom: 8 }}>
          {PLANT_STAGES.map((s, i) => (
            <div key={s} style={{
              width: 32, height: 32, borderRadius: "50%",
              background: i <= stageIdx ? T.sage : T.parchmentDark,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 14, transition: "all 0.3s",
            }}>
              <PlantSVG stage={s} size={24} />
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: T.textMuted }}>Stage {stageIdx + 1} of {PLANT_STAGES.length}</p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div className="card fade-up-2" style={{ textAlign: "center" }}>
          <p style={{ fontFamily: "Lora, serif", fontSize: 36, fontWeight: 600, color: T.sage }}>{checkIns}</p>
          <p style={{ fontSize: 13, color: T.textSecondary, marginTop: 4 }}>times you showed up</p>
        </div>
        <div className="card fade-up-2" style={{ textAlign: "center" }}>
          <p style={{ fontFamily: "Lora, serif", fontSize: 36, fontWeight: 600, color: T.clay }}>{daysActive}</p>
          <p style={{ fontSize: 13, color: T.textSecondary, marginTop: 4 }}>days of practice</p>
        </div>
      </div>

      {/* Philosophy note */}
      <div className="card fade-up-3" style={{ background: T.parchmentDark, border: "none" }}>
        <p style={{ fontFamily: "Lora, serif", fontStyle: "italic", fontSize: 14, color: T.textSecondary, lineHeight: 1.8, textAlign: "center" }}>
          "Progress here isn't about perfect days.<br />
          It's about the moments you chose to notice."
        </p>
      </div>
    </div>
  );
};

// ── Bottom Navigation ─────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { id: "checkin", label: "Today", icon: "○" },
  { id: "insights", label: "Insights", icon: "◈" },
  { id: "history", label: "History", icon: "≡" },
  { id: "plant", label: "Plant", icon: "❧" },
];

const BottomNav = ({ current, onChange }) => (
  <div style={{
    position: "fixed", bottom: 0, left: 0, right: 0,
    background: T.surface, borderTop: `1px solid ${T.border}`,
    padding: "10px 16px 24px", display: "flex", justifyContent: "space-around",
    backdropFilter: "blur(12px)", zIndex: 100,
  }}>
    {NAV_ITEMS.map(item => (
      <button key={item.id} className={`nav-btn ${current === item.id ? "active" : ""}`}
        onClick={() => onChange(item.id)}>
        <span style={{ fontSize: 20 }}>{item.icon}</span>
        <span>{item.label}</span>
      </button>
    ))}
  </div>
);

// ── API ───────────────────────────────────────────────────────────────────────
const API_BASE = "https://ww116obsv3.execute-api.us-east-1.amazonaws.com/Prod";
const USER_ID = "default";

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [screen, setScreen] = useState("welcome");
  const [entries, setEntries] = useState([]);
  const [plantData, setPlantData] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [entriesRes, plantRes] = await Promise.all([
        fetch(`${API_BASE}/entries?user_id=${USER_ID}`),
        fetch(`${API_BASE}/plant?user_id=${USER_ID}`),
      ]);
      const entriesData = await entriesRes.json();
      const plantDataJson = await plantRes.json();
      setEntries(Array.isArray(entriesData) ? entriesData : []);
      setPlantData(plantDataJson);
    } catch (err) {
      console.error("Error loading data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleBegin = () => {
    loadData();
    setScreen("checkin");
  };

  const handleSubmitEntry = async (entry) => {
    try {
      await fetch(`${API_BASE}/entries`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...entry, user_id: USER_ID }),
      });

      // Save triggers as patterns
      for (const trigger of (entry.triggers || [])) {
        await fetch(`${API_BASE}/patterns`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: USER_ID, trigger, stress_level: entry.stress_level }),
        });
      }

      await loadData();
    } catch (err) {
      console.error("Error saving entry:", err);
    }
  };

  const handleDelete = async (id) => {
    try {
      await fetch(`${API_BASE}/entries/${id}?user_id=${USER_ID}`, { method: "DELETE" });
      await loadData();
    } catch (err) {
      console.error("Error deleting entry:", err);
    }
  };

  if (screen === "welcome") {
    return (
      <>
        <FontLoader />
        <GlobalStyles />
        <div className="wn-app">
          <WelcomeScreen onBegin={handleBegin} />
        </div>
      </>
    );
  }

  const handleTabChange = (tab) => {
    setScreen(tab);
    loadData();
  };

  return (
    <>
      <FontLoader />
      <GlobalStyles />
      <div className="wn-app wn-center" style={{ paddingBottom: 0 }}>
        {loading && (
          <div style={{ position: "fixed", top: 0, left: 0, right: 0, height: 3, background: T.sage, zIndex: 999, opacity: 0.8 }} />
        )}
        {screen === "checkin" && <CheckInScreen onSubmit={handleSubmitEntry} />}
        {screen === "insights" && <InsightsScreen entries={entries} />}
        {screen === "history" && <HistoryScreen entries={entries} onDelete={handleDelete} />}
        {screen === "plant" && <PlantScreen plantData={plantData} entries={entries} />}
        <BottomNav current={screen} onChange={handleTabChange} />
      </div>
    </>
  );
}