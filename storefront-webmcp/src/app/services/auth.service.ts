// Copyright 2026 UCP Authors / GDG DevFest Milano 2026
import { Injectable, signal, computed } from '@angular/core';
import { initializeApp, getApps, FirebaseApp } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  signOut,
  GoogleAuthProvider,
  onAuthStateChanged,
  User,
  Auth
} from 'firebase/auth';
import { environment } from '../../environments/environment';

export interface UserProfile {
  uid: string;
  email: string | null;
  displayName: string | null;
  photoURL: string | null;
  loyaltyTier?: string;
  loyaltyCode?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private app: FirebaseApp;
  private auth: Auth;
  private provider: GoogleAuthProvider;

  readonly user = signal<UserProfile | null>(null);
  readonly loading = signal<boolean>(true);
  readonly error = signal<string | null>(null);

  readonly isAuthenticated = computed(() => !!this.user());
  readonly userDisplayName = computed(() => this.user()?.displayName || this.user()?.email || 'Viaggiatore Google');
  readonly userEmail = computed(() => this.user()?.email || 'viaggiatore@devfest.it');
  readonly userAvatar = computed(() => this.user()?.photoURL || null);
  readonly loyaltyTier = computed(() => this.user()?.loyaltyTier || 'FrecciaClub Gold');
  readonly loyaltyCode = computed(() => {
    const u = this.user();
    if (!u) return 'FF-884920';
    if (u.loyaltyCode) return u.loyaltyCode;
    return 'FF-' + (u.uid ? u.uid.slice(-6).toUpperCase() : '884920');
  });

  constructor() {
    this.app = getApps().length === 0 ? initializeApp(environment.firebase) : getApps()[0];
    this.auth = getAuth(this.app);
    this.provider = new GoogleAuthProvider();
    this.provider.setCustomParameters({ prompt: 'select_account' });

    onAuthStateChanged(this.auth, async (firebaseUser: User | null) => {
      if (firebaseUser) {
        await this.syncUserWithMerchant(firebaseUser);
      } else {
        this.user.set(null);
      }
      this.loading.set(false);
    });
  }

  async syncUserWithMerchant(firebaseUser: User): Promise<void> {
    const email = firebaseUser.email || '';
    try {
      const res = await fetch(`${environment.bopisApiUrl}/merchant/users/verify?email=${encodeURIComponent(email)}`);
      if (res.ok) {
        const data = await res.json();
        const reg = data.user || {};
        this.user.set({
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          displayName: reg.display_name || firebaseUser.displayName || 'Andrea Alberto',
          photoURL: firebaseUser.photoURL,
          loyaltyTier: reg.loyalty_tier || 'FrecciaClub Gold',
          loyaltyCode: reg.loyalty_code || 'FF-AA2026'
        });
        this.error.set(null);
      } else {
        const err = await res.json().catch(() => ({}));
        this.user.set({
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          displayName: firebaseUser.displayName || 'Utente Non Censito',
          photoURL: firebaseUser.photoURL,
          loyaltyTier: 'Ospite',
          loyaltyCode: 'NON-REGISTRATO'
        });
        this.error.set(err.error || `L'account '${email}' non è censito nella collezione merchant_users. Registrazione manuale richiesta.`);
      }
    } catch {
      this.user.set({
        uid: firebaseUser.uid,
        email: firebaseUser.email,
        displayName: firebaseUser.displayName || 'Andrea Alberto',
        photoURL: firebaseUser.photoURL,
        loyaltyTier: 'FrecciaClub Gold',
        loyaltyCode: 'FF-AA2026'
      });
    }
  }

  async loginWithGoogle(): Promise<void> {
    this.error.set(null);
    try {
      const result = await signInWithPopup(this.auth, this.provider);
      await this.syncUserWithMerchant(result.user);
    } catch (err: any) {
      console.warn('Google Sign-In fallito o annullato:', err);
      this.error.set(err.message || 'Errore durante il login con Google');
      throw err;
    }
  }

  async logout(): Promise<void> {
    this.user.set(null);
    try {
      await signOut(this.auth);
    } catch (err) {
      console.error('Logout error:', err);
    }
  }

  // Quick fallback for demo simulation if offline
  loginDemoUser(): void {
    this.user.set({
      uid: 'usr-alex-rossi',
      email: 'alex.traveler@example.com',
      displayName: 'Alex Rossi',
      photoURL: null,
      loyaltyTier: 'FrecciaClub Gold',
      loyaltyCode: 'FF-AR2026'
    });
  }
}
