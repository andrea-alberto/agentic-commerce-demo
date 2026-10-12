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
  readonly isOperator = signal<boolean>(false);
  readonly operatorChecked = signal<boolean>(false);

  readonly isAuthenticated = computed(() => !!this.user());
  readonly userDisplayName = computed(() => this.user()?.displayName || this.user()?.email || 'Operatore Stazione');
  readonly userAvatar = computed(() => this.user()?.photoURL || null);

  constructor() {
    this.app = getApps().length === 0 ? initializeApp(environment.firebase) : getApps()[0];
    this.auth = getAuth(this.app);
    this.provider = new GoogleAuthProvider();
    this.provider.setCustomParameters({ prompt: 'select_account' });

    onAuthStateChanged(this.auth, async (firebaseUser: User | null) => {
      if (firebaseUser) {
        this.user.set({
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          displayName: firebaseUser.displayName,
          photoURL: firebaseUser.photoURL
        });
        await this.verifyOperator(firebaseUser.email);
      } else {
        this.user.set(null);
        this.isOperator.set(false);
        this.operatorChecked.set(true);
      }
      this.loading.set(false);
    });
  }

  async verifyOperator(email: string | null): Promise<boolean> {
    if (!email) {
      this.isOperator.set(false);
      this.operatorChecked.set(true);
      return false;
    }
    try {
      const res = await fetch(`${environment.bopisApiUrl}/merchant/users/verify?email=${encodeURIComponent(email)}`);
      if (res.ok) {
        const data = await res.json();
        const allowed = !!data.is_operator;
        this.isOperator.set(allowed);
        this.operatorChecked.set(true);
        return allowed;
      } else {
        this.isOperator.set(false);
        this.operatorChecked.set(true);
        return false;
      }
    } catch (e) {
      console.warn('Verifica operatore offline, fallback locale:', e);
      // Fallback per operatore demo locale
      const isMaster = email.trim().toLowerCase() === 'merchant@agentic-commerce.demo' || email.includes('merchant');
      this.isOperator.set(isMaster);
      this.operatorChecked.set(true);
      return isMaster;
    }
  }

  async loginWithGoogle(): Promise<void> {
    this.error.set(null);
    try {
      const result = await signInWithPopup(this.auth, this.provider);
      const u = result.user;
      this.user.set({
        uid: u.uid,
        email: u.email,
        displayName: u.displayName,
        photoURL: u.photoURL
      });
      await this.verifyOperator(u.email);
    } catch (err: any) {
      console.warn('Google Sign-In fallito o annullato:', err);
      this.error.set(err.message || 'Errore durante il login con account Google');
      throw err;
    }
  }

  async logout(): Promise<void> {
    this.user.set(null);
    this.isOperator.set(false);
    this.operatorChecked.set(true);
    try {
      await signOut(this.auth);
    } catch (err) {
      console.error('Logout error:', err);
    }
  }
}
