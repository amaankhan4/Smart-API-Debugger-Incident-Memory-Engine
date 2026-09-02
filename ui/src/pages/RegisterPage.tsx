import { AlertCircle, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { errorMessage } from 'api/client';
import { AuthLayout } from 'layouts/AuthLayout';
import { useAuthStore } from 'store/useAuthStore';

const MIN_PASSWORD_LENGTH = 8;

export const RegisterPage = () => {
  const register = useAuthStore((state) => state.register);
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const passwordTooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (passwordTooShort) return;

    setError(null);
    setSubmitting(true);
    try {
      await register(email, name, password);
      navigate('/overview', { replace: true });
    } catch (caught) {
      setError(errorMessage(caught, 'Unable to create the account'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start turning raw logs into searchable incident memory."
      footer={
        <>
          Already registered?{' '}
          <Link to="/login" className="text-accent-soft hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-severity-critical/40 bg-severity-critical/10 px-3 py-2 text-xs text-severity-critical"
          >
            <AlertCircle size={14} className="mt-0.5 shrink-0" aria-hidden />
            <span>{error}</span>
          </div>
        )}

        <div>
          <label htmlFor="name" className="mb-1.5 block text-xs font-medium text-content-muted">
            Name
          </label>
          <input
            id="name"
            required
            autoComplete="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="input"
            placeholder="Ada Lovelace"
          />
        </div>

        <div>
          <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-content-muted">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="input"
            placeholder="you@company.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-content-muted">
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            aria-invalid={passwordTooShort}
            aria-describedby="password-hint"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="input"
            placeholder="••••••••"
          />
          <p
            id="password-hint"
            className={`mt-1.5 text-2xs ${passwordTooShort ? 'text-severity-critical' : 'text-content-subtle'}`}
          >
            At least {MIN_PASSWORD_LENGTH} characters.
          </p>
        </div>

        <button
          type="submit"
          disabled={submitting || passwordTooShort}
          className="btn-primary w-full"
        >
          {submitting && <Loader2 size={14} className="animate-spin" aria-hidden />}
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
    </AuthLayout>
  );
};
