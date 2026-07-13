import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { GoogleLogin } from '@react-oauth/google'
import LogoLight from '../assets/logo-light-bg.svg'

const CRM_URL = 'https://automationgini-crmv2.onrender.com'
const API_BASE = 'https://automationgini-api.onrender.com'
const SIGNUP_API = `${API_BASE}/auth/signup`
const LOGIN_API = `${API_BASE}/auth/login`
const GOOGLE_AUTH_API = `${API_BASE}/auth/google`

export default function Auth({ initialMode = 'signup' }) {
  const [searchParams] = useSearchParams()
  const urlMode = searchParams.get('mode')
  const [accountType, setAccountType] = useState('individual') // 'individual' | 'agency_owner' | 'agent'
  const [mode, setMode] = useState(urlMode === 'signin' || urlMode === 'signup' ? urlMode : initialMode)
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [message, setMessage] = useState('')

  const [form, setForm] = useState({
    firstName: '', lastName: '', company: '', email: '', password: '',
  })

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  function redirectToCRM(accessToken, name) {
    setTimeout(() => {
      window.location.href = `${CRM_URL}/auth/callback?token=${encodeURIComponent(accessToken)}`
    }, 1200)
  }

  async function handleSignup(e) {
    e.preventDefault()
    if (!form.firstName.trim() || !form.lastName.trim() || !form.company.trim() || !form.email.trim() || !form.password) {
      setStatus('error'); setMessage('Fill in every field first.'); return
    }
    if (form.password.length < 8) {
      setStatus('error'); setMessage('Password needs to be at least 8 characters.'); return
    }
    setStatus('loading')
    try {
      const resp = await fetch(SIGNUP_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: form.firstName, last_name: form.lastName,
          company_name: form.company, email: form.email, password: form.password,
        }),
      })
      const data = await resp.json()
      if (resp.ok) {
        setStatus('success')
        setMessage('Account created! Taking you to your dashboard...')
        redirectToCRM(data.access_token, data.full_name)
      } else {
        setStatus('error'); setMessage(data.detail || 'Something went wrong.')
      }
    } catch {
      setStatus('error'); setMessage("Couldn't reach the server. Try again in a moment.")
    }
  }

  async function handleSignin(e) {
    e.preventDefault()
    if (!form.email.trim() || !form.password) {
      setStatus('error'); setMessage('Enter your email and password.'); return
    }
    setStatus('loading')
    try {
      const resp = await fetch(LOGIN_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: form.email, password: form.password }),
      })
      const data = await resp.json()
      if (resp.ok) {
        setStatus('success')
        setMessage(`Welcome back, ${data.full_name.split(' ')[0]}! Redirecting to your dashboard...`)
        redirectToCRM(data.access_token, data.full_name)
      } else {
        setStatus('error'); setMessage(data.detail || 'Invalid email or password.')
      }
    } catch {
      setStatus('error'); setMessage("Couldn't reach the server. Try again in a moment.")
    }
  }

  async function handleGoogleAuth(credentialResponse) {
    if (!credentialResponse.credential) return
    setStatus('loading')
    try {
      const resp = await fetch(GOOGLE_AUTH_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential, account_type: accountType }),
      })
      const data = await resp.json()
      if (resp.ok) {
        setStatus('success')
        setMessage(`Welcome${data.full_name ? ', ' + data.full_name.split(' ')[0] : ''}! Redirecting to your dashboard...`)
        redirectToCRM(data.access_token, data.full_name)
      } else {
        setStatus('error'); setMessage(data.detail || 'Google sign-in failed.')
      }
    } catch {
      setStatus('error'); setMessage("Couldn't reach the server. Try again in a moment.")
    }
  }

  function switchMode(next) {
    setMode(next)
    if (next === 'signup') setAccountType('individual')
    setStatus('idle'); setMessage('')
  }

  function switchAccountType(next) {
    setAccountType(next)
    if (next === 'agent' || next === 'agency_owner') setMode('signin')
    setStatus('idle'); setMessage('')
  }

  return (
    <div className="min-h-screen bg-navy relative overflow-hidden flex items-center justify-center px-6 py-12">
      {/* Ambient glow, matching hero */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-32 -right-40 w-[560px] h-[560px] rounded-full bg-blue/20 blur-[120px]" />
        <div className="absolute bottom-0 -left-20 w-[420px] h-[420px] rounded-full bg-amber/10 blur-[100px]" />
      </div>

      {/* Decorative blurred product backdrop */}
      <div className="pointer-events-none absolute inset-0 blur-md opacity-40">
        <div className="h-16 bg-navy-deep flex items-center gap-7 px-8">
          {[1, 2, 3, 4].map((i) => <div key={i} className="w-20 h-3.5 rounded bg-white/15" />)}
        </div>
        <div className="flex gap-5 p-8">
          <div className="flex-1 max-w-[220px] bg-white rounded-2xl p-5 space-y-3">
            <div className="h-3 w-3/5 bg-slate-200 rounded" />
            <div className="h-3 w-full bg-slate-200 rounded" />
            <div className="h-3 w-full bg-slate-200 rounded" />
          </div>
          <div className="flex-[2] bg-white rounded-2xl p-5">
            <div className="font-mono text-4xl font-bold text-blue mb-2">116</div>
            <div className="h-3 w-2/5 bg-slate-200 rounded mb-5" />
            <div className="h-3 w-full bg-amber/20 rounded" />
          </div>
        </div>
      </div>

      {/* Auth card */}
      <div className="relative z-10 w-full max-w-md">
        <div className="flex justify-center mb-7">
          <img src={LogoLight} alt="AutomationGini" className="h-9" />
        </div>

        <div className="bg-white rounded-2xl shadow-2xl shadow-black/30 p-8">
          {mode === 'signin' && (
            <>
              <div className="flex justify-center gap-1 mb-5 bg-slate-50 rounded-full p-1 w-fit mx-auto">
                <button
                  onClick={() => switchAccountType('individual')}
                  className={`font-body font-semibold text-xs px-3.5 py-1.5 rounded-full transition-colors ${
                    accountType === 'individual' ? 'bg-navy text-white' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  Individual
                </button>
                <button
                  onClick={() => switchAccountType('agency_owner')}
                  className={`font-body font-semibold text-xs px-3.5 py-1.5 rounded-full transition-colors ${
                    accountType === 'agency_owner' ? 'bg-navy text-white' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  Agency Owner
                </button>
                <button
                  onClick={() => switchAccountType('agent')}
                  className={`font-body font-semibold text-xs px-3.5 py-1.5 rounded-full transition-colors ${
                    accountType === 'agent' ? 'bg-navy text-white' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  Agent
                </button>
              </div>

              {accountType === 'agent' && (
                <p className="text-center text-sm text-slate mb-5">
                  Use the credentials your agency admin gave you.
                </p>
              )}
              {accountType === 'agency_owner' && (
                <p className="text-center text-sm text-slate mb-5">
                  Sign in with the credentials AutomationGini provided you.
                </p>
              )}
            </>
          )}

          {accountType === 'individual' && (
            <div className="grid grid-cols-2 gap-2 mb-6">
              <button
                onClick={() => switchMode('signin')}
                className={`font-body font-semibold text-sm py-2.5 rounded-lg transition-colors ${
                  mode === 'signin' ? 'bg-navy text-white' : 'bg-slate-100 text-slate hover:bg-slate-200'
                }`}
              >
                Sign In
              </button>
              <button
                onClick={() => switchMode('signup')}
                className={`font-body font-semibold text-sm py-2.5 rounded-lg transition-colors ${
                  mode === 'signup' ? 'bg-navy text-white' : 'bg-slate-100 text-slate hover:bg-slate-200'
                }`}
              >
                Sign Up
              </button>
            </div>
          )}

          {mode === 'signup' && (
            <p className="text-center text-sm text-slate mb-5">
              Free plan — 100 leads, 5 voice demos, 5 chatbot demos. No card required.
            </p>
          )}

          {status === 'success' ? (
            <div className="text-center py-6">
              <div className="w-12 h-12 rounded-full bg-green-100 text-green-600 flex items-center justify-center mx-auto mb-4 text-2xl">
                ✓
              </div>
              <p className="font-body text-navy font-medium">{message}</p>
            </div>
          ) : (
            <>
              <div className="flex justify-center mb-4">
                <GoogleLogin
                  onSuccess={handleGoogleAuth}
                  onError={() => { setStatus('error'); setMessage('Google sign-in failed.') }}
                  text={mode === 'signup' ? 'signup_with' : 'signin_with'}
                  shape="rectangular"
                  width="304"
                />
              </div>
              <div className="flex items-center gap-3 mb-4 text-xs text-slate-400">
                <span className="flex-1 h-px bg-slate-200" />
                or
                <span className="flex-1 h-px bg-slate-200" />
              </div>

              <form onSubmit={mode === 'signup' ? handleSignup : handleSignin} className="space-y-4">
              {mode === 'signup' && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <Field label="First name" value={form.firstName} onChange={update('firstName')} />
                    <Field label="Last name" value={form.lastName} onChange={update('lastName')} />
                  </div>
                  <Field label="Company name" value={form.company} onChange={update('company')} />
                </>
              )}
              <Field label={mode === 'signup' ? 'Business email' : 'Email or username'} type={mode === 'signup' ? 'email' : 'text'} value={form.email} onChange={update('email')} />
              <Field label="Password" type="password" value={form.password} onChange={update('password')} />

              {status === 'error' && (
                <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{message}</p>
              )}

              <button
                type="submit"
                disabled={status === 'loading'}
                className="w-full font-body font-semibold text-white bg-blue hover:bg-blue-light disabled:opacity-60 rounded-lg py-3 transition-colors"
              >
                {status === 'loading' ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Log in'}
              </button>
            </form>
            </>
          )}

          {status !== 'success' && accountType === 'individual' && (
            <p className="text-center text-sm text-slate mt-5">
              {mode === 'signup' ? (
                <>Already have an account?{' '}
                  <button onClick={() => switchMode('signin')} className="text-blue font-semibold hover:underline">
                    Sign in
                  </button>
                </>
              ) : (
                <>New here?{' '}
                  <button onClick={() => switchMode('signup')} className="text-blue font-semibold hover:underline">
                    Sign up free
                  </button>
                </>
              )}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function Field({ label, type = 'text', value, onChange }) {
  return (
    <label className="block">
      <span className="block text-xs font-semibold text-slate-600 uppercase tracking-wide mb-1.5">{label}</span>
      <input
        type={type}
        value={value}
        onChange={onChange}
        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 text-navy font-body text-sm focus:outline-none focus:ring-2 focus:ring-blue/40 focus:border-blue"
      />
    </label>
  )
}
