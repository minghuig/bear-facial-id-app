import {Alert, Button} from '@mui/material';
import {ResearchCreditLinks} from './ResearchCredits';

export function SignInPage(){
 return <main className="signin-page">
  <div className="signin-shell">
   <section className="signin-copy" aria-labelledby="welcome-title">
    <a className="signin-brand" href="/" aria-label="Only Bears home"><img src="/bear.svg" width="52" height="52" alt=""/><span>Only Bears</span></a>
    <div className="signin-welcome">
     <span className="signin-eyebrow">Familiar faces. Wild places.</span>
     <h1 id="welcome-title">Every bear<br/>has a story.</h1>
     <p>A little closer to knowing who's who. Bring your field photos together, find familiar bears, and build a shared library with your team.</p>
     {window.location.search.includes('login=denied')&&<Alert severity="warning">We couldn't sign you in. Use your invited Google account, or ask the project owner for access.</Alert>}
     <Button className="signin-button" variant="contained" href="/auth/login"><span className="signin-google" aria-hidden="true">G</span>Continue with Google<span aria-hidden="true">↗</span></Button>
     <div className="signin-invite">Your team's private library · Invitation required</div>
    </div>
    <div className="signin-footer"><span>Made for curious humans. And very good bears.</span><ResearchCreditLinks/></div>
   </section>
   <figure className="signin-photo">
    <img src="/welcome-bear.jpg" alt="A brown bear resting its head on its paws beside a rocky stream" fetchPriority="high"/>
    <figcaption><span className="signin-photo-tag">Out in the wild</span><span>Take a closer look.<br/>Get to know a bear.</span></figcaption>
   </figure>
  </div>
 </main>;
}
