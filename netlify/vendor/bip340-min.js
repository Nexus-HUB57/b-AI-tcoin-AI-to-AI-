// BIP-340 Schnorr minimal (secp256k1, BigInt puro) - fallback offline
(function(){
const P=BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F");
const N=BigInt("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141");
const Gx=BigInt("0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798");
const Gy=BigInt("0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8");
function mod(a,m){a=a%m;return a<0n?a+m:a}
function inv(a,m){let lm=1n,hm=0n,low=mod(a,m),high=m;while(low>1n){let r=high/low;let nm=hm-lm*r,nw=high-low*r;hm=lm;high=low;lm=nm;low=nw}return mod(lm,m)}
function add(a,b){if(!a)return b;if(!b)return a;let s;if(a[0]===b[0]){if(a[1]!==b[1])return null;s=mod(3n*a[0]*a[0]*inv(2n*a[1],P),P)}else{s=mod((b[1]-a[1])*inv(b[0]-a[0],P),P)}const rx=mod(s*s-a[0]-b[0],P);return [rx,mod(s*(a[0]-rx)-a[1],P)]}
function mul(k,p){let r=null,a=p;while(k>0n){if(k&1n)r=add(r,a);a=add(a,a);k>>=1n}return r}
function liftX(x){const y2=mod(x*x*x+7n,P);const y=modPow(y2,(P+1n)/4n,P);if(mod(y*y,P)!==y2)throw "bad x";return [x,(y&1n)?P-y:y]}
function modPow(b,e,m){let r=1n;b=mod(b,m);while(e>0n){if(e&1n)r=mod(r*b,m);b=mod(b*b,m);e>>=1n}return r}
function hx(b){return b.toString(16).padStart(64,"0")}
async function th(tag,msg){const h=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(tag));
const t=new Uint8Array(h);const m=typeof msg==="string"?new TextEncoder().encode(msg):msg;
const c=new Uint8Array(t.length*2+m.length);c.set(t,0);c.set(t,t.length);c.set(m,t.length*2);
return BigInt("0x"+Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",c))).map(x=>x.toString(16).padStart(2,"0")).join(""))}
async function schnorrSign(privHex,msgHex){
const d0=BigInt("0x"+privHex);const Ppt=mul(d0,[Gx,Gy]);
const d=(Ppt[1]&1n)?N-d0:d0;
const m=BigInt("0x"+msgHex);
const t=d^await th("BIP0340/aux",new Uint8Array(32));
const k0=mod(await th("BIP0340/nonce",hx(t)+hx(Ppt[0])+msgHex),N);
const R=mul(k0,[Gx,Gy]);const k=(R[1]&1n)?N-k0:k0;
const e=mod(await th("BIP0340/challenge",hx(R[0])+hx(Ppt[0])+msgHex),N);
const s=mod(k+e*d,N);
return {r:hx(R[0]),s:hx(s),pubkey:hx(Ppt[0]),sig:hx(R[0])+hx(s)};
}
async function schnorrVerify(pubHex,msgHex,sigHex){
const r=BigInt("0x"+sigHex.slice(0,64)),s=BigInt("0x"+sigHex.slice(64));
const e=mod(await th("BIP0340/challenge",sigHex.slice(0,64)+pubHex+msgHex),N);
const R=add(mul(s,[Gx,Gy]),mul(N-e,liftX(BigInt("0x"+pubHex))));
return R&&!(R[1]&1n)&&R[0]===r;
}
window.BIP340={sign:schnorrSign,verify:schnorrVerify};
})();
