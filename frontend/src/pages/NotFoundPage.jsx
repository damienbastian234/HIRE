import { Link } from "react-router-dom";
import { FiArrowLeft } from "react-icons/fi";
import Button from "../components/Button";

export default function NotFoundPage() {
  return (
    <div className="container-page flex min-h-[70vh] flex-col items-center justify-center text-center">
      <span className="font-display text-7xl font-semibold text-ink/10">404</span>
      <h1 className="mt-4 text-2xl font-semibold">This page isn't in our pipeline</h1>
      <p className="mt-2 max-w-sm text-sm text-slate">
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link to="/" className="mt-7">
        <Button variant="signal" size="lg">
          <FiArrowLeft /> Back to home
        </Button>
      </Link>
    </div>
  );
}
