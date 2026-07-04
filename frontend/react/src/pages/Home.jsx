import { Link } from "react-router-dom";
import {
  Leaf,
  Satellite,
  ShieldCheck,
  MapPin,
  Trees,
  Radar,
  ArrowRight,
  Mail,
  Phone,
  MapPinned,
  Droplets,
  Waves,
} from "lucide-react";
import { useAuth } from "../AuthContext.jsx";
import "./Home.css";

export default function Home() {
  const { isLoggedIn } = useAuth();

  return (
    <div className="home">
      {/* ===== Nav ===== */}
      <nav className="home-nav">
        <div className="home-nav-brand">
          <Leaf size={22} />
          <span>Eco-Guard</span>
        </div>
        <div className="home-nav-links">
          <a href="#forests">Forests</a>
          <a href="#water">Water Resources</a>
          <a href="#awareness">Our Mission</a>
          <a href="#contact">Contact</a>
        </div>
        <div className="home-nav-actions">
          {isLoggedIn ? (
            <>
              <Link to="/tool" className="home-nav-link">Forest Tool</Link>
              <Link to="/water-tool" className="home-nav-btn">
                Water Tool <ArrowRight size={15} />
              </Link>
            </>
          ) : (
            <>
              <Link to="/login" className="home-nav-link">Log in</Link>
              <Link to="/register" className="home-nav-btn">Register</Link>
            </>
          )}
        </div>
      </nav>

      {/* ===== Hero ===== */}
      <header className="hero">
        <div className="hero-glow" />
        <div className="hero-icon-cluster">
          <Trees size={140} strokeWidth={1} />
        </div>
        <div className="hero-content">
          <span className="hero-eyebrow">
            <Radar size={13} /> Satellite monitoring · Forests &amp; Water · Telangana
          </span>
          <h1>Protecting Telangana's Forests and Water Bodies, One Satellite Pass at a Time</h1>
          <p>
            Eco-Guard combines Google Earth Engine NDVI and NDWI analysis with real-time alerts to
            detect illegal deforestation and shrinking lakes and reservoirs across Telangana —
            before it's too late.
          </p>
          <div className="hero-actions">
            <Link to={isLoggedIn ? "/tool" : "/register"} className="hero-btn-primary">
              <Satellite size={17} /> Start Monitoring
            </Link>
            <a href="#forests" className="hero-btn-ghost">
              Learn more
            </a>
          </div>
        </div>
      </header>

      {/* ===== Forest section ===== */}
      <section className="section" id="forests">
        <span className="section-eyebrow">
          <Leaf size={13} /> Forest monitoring
        </span>
        <h2>Monitoring forest change across six Telangana districts</h2>
        <p className="section-lead">
          Eco-Guard tracks vegetation health using Sentinel-2 satellite imagery and NDVI
          (Normalized Difference Vegetation Index) analysis, comparing forest cover between time
          periods to flag sudden vegetation loss consistent with illegal logging or land clearing.
        </p>
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon green">
              <Satellite size={22} />
            </div>
            <h3>Satellite NDVI Analysis</h3>
            <p>Live Google Earth Engine data compares before/after vegetation health for any region.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon yellow">
              <MapPin size={22} />
            </div>
            <h3>Six Telangana Regions</h3>
            <p>Hyderabad, Warangal, Khammam, Nizamabad, Karimnagar, and Mahbubnagar forest belts.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon blue">
              <ShieldCheck size={22} />
            </div>
            <h3>Verified Admin Review</h3>
            <p>Every flagged change is reviewed and marked legal or illegal by an accountable admin.</p>
          </div>
        </div>
      </section>

      {/* ===== Water section ===== */}
      <section className="section section-alt" id="water">
        <span className="section-eyebrow water">
          <Droplets size={13} /> Water resource monitoring
        </span>
        <h2>Watching over Telangana's lakes and reservoirs</h2>
        <p className="section-lead">
          Using the same satellite backbone, Eco-Guard analyzes NDWI (Normalized Difference Water
          Index) to detect shrinking water spread in major lakes and reservoirs — an early signal
          of drought stress, encroachment, or illegal draining.
        </p>
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon blue">
              <Waves size={22} />
            </div>
            <h3>Satellite NDWI Analysis</h3>
            <p>Compares water-spread area between time periods for each monitored lake/reservoir.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon green">
              <Droplets size={22} />
            </div>
            <h3>Six Major Water Bodies</h3>
            <p>Hussain Sagar, Osman Sagar, Himayat Sagar, Nagarjuna Sagar, Nizam Sagar, Singur Dam.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon yellow">
              <ShieldCheck size={22} />
            </div>
            <h3>Same Verified Workflow</h3>
            <p>Shrinkage events go through the same admin legal/illegal review and alert pipeline.</p>
          </div>
        </div>
      </section>

      {/* ===== Awareness / Mission message ===== */}
      <section className="awareness" id="awareness">
        <Trees className="awareness-icon" size={40} strokeWidth={1.25} />
        <blockquote>
          "The Earth does not belong to us; we belong to the Earth. Every hectare of forest and
          every drop of water we save today is a promise kept to tomorrow."
        </blockquote>
        <p className="awareness-sub">
          Telangana's forests and lakes sustain countless species and communities. Illegal
          deforestation and vanishing water bodies don't just remove trees or water — they disrupt
          rainfall, accelerate soil erosion, and threaten the balance of entire ecosystems. Join us
          in watching over them.
        </p>
      </section>

      {/* ===== Footer ===== */}
      <footer className="home-footer" id="contact">
        <div className="footer-grid">
          <div>
            <div className="home-nav-brand" style={{ marginBottom: "0.75rem" }}>
              <Leaf size={20} />
              <span>Eco-Guard</span>
            </div>
            <p className="footer-tagline">
              Satellite-powered forest and water monitoring for Telangana, built to protect what
              can't speak for itself.
            </p>
          </div>
          <div>
            <h4>Contact</h4>
            <p><Mail size={14} /> contact@ecoguard.example.org</p>
            <p><Phone size={14} /> +91 40 2345 0000</p>
            <p><MapPinned size={14} /> Hyderabad, Telangana, India</p>
          </div>
          <div>
            <h4>Quote</h4>
            <p className="footer-quote">
              "In every walk with nature, one receives far more than he seeks." — John Muir
            </p>
          </div>
        </div>
        <div className="footer-bottom">
          © {new Date().getFullYear()} Eco-Guard Telangana. Built for forest and water conservation.
        </div>
      </footer>
    </div>
  );
}