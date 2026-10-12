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

  readonly isAuthenticated = computed(() => !!this.user());
  readonly userDisplayName = computed(() => this.user()?.displayName || this.user()?.email || 'Utente Google');
  readonly userAvatar = computed(() => this.user()?.photoURL || null);

  constructor() {
    this.app = getApps().length === 0 ? initializeApp(environment.firebase) : getApps()[0];
    this.auth = getAuth(this.app);
    this.provider = new GoogleAuthProvider();
    this.provider.setCustomParameters({ prompt: 'select_account' });

    onAuthStateChanged(this.auth, (firebaseUser: User | null) => {
      if (firebaseUser) {
        this.user.set({
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          displayName: firebaseUser.displayName,
          photoURL: firebaseUser.photoURL
        });
      } else {
        this.user.set(null);
      }
      this.loading.set(false);
    });
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
    } catch (err: any) {
      console.warn('Google Sign-In fallito o annullato:', err);
      this.error.set(err.message || 'Errore durante il login con account Google');
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
}
