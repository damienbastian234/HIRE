import { FiTarget, FiMic, FiShield, FiTrendingUp } from "react-icons/fi";
import Hero from "../components/Hero";
import FeatureCard from "../components/FeatureCard";
import JobCard from "../components/JobCard";
import { mockJobs } from "../services/mockData";

const FEATURES = [
  {
    icon: <FiTarget size={18} />,
    title: "Explainable match scores",
    description: "Every score breaks down into skills, experience, and location fit — not a black box.",
  },
  {
    icon: <FiMic size={18} />,
    title: "AI interview practice",
    description: "Candidates rehearse real questions and get structured feedback before the real thing.",
  },
  {
    icon: <FiTrendingUp size={18} />,
    title: "Recruiter-ready pipelines",
    description: "Recruiters see ranked candidates with the same transparent scoring, no guesswork.",
  },
  {
    icon: <FiShield size={18} />,
    title: "Bias-aware ranking",
    description: "Scoring weights are visible and auditable, so ranking logic can be reviewed, not assumed.",
  },
];

export default function LandingPage() {
  const featured = mockJobs.slice(0, 3);

  return (
    <>
      <Hero />

      <section className="border-t border-ink/8 bg-white py-16">
        <div className="container-page">
          <span className="eyebrow">Why H.I.R.E.</span>
          <h2 className="mt-3 max-w-xl text-2xl font-semibold sm:text-3xl">
            Built to make hiring decisions easier to trust
          </h2>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature, index) => (
              <FeatureCard key={feature.title} {...feature} index={index} />
            ))}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="container-page">
          <div className="flex items-end justify-between">
            <div>
              <span className="eyebrow">Open roles</span>
              <h2 className="mt-3 text-2xl font-semibold sm:text-3xl">Recently posted</h2>
            </div>
          </div>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
