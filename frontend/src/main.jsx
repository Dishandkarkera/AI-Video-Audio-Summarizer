import React, {useEffect, useState} from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import SummaryPage from './components/SummaryPage';
import './styles.css';

function Router(){
	const [hash, setHash] = useState(window.location.hash);
	useEffect(()=>{
		const handler = ()=>setHash(window.location.hash);
		window.addEventListener('hashchange', handler);
		return ()=>window.removeEventListener('hashchange', handler);
	},[]);
	if(hash.startsWith('#/summary/')){
		const id = parseInt(hash.split('/')[2]);
		if(!isNaN(id)) return <SummaryPage mediaId={id} />;
	}
	return <App />;
}

createRoot(document.getElementById('root')).render(
	<ErrorBoundary>
		<Router />
	</ErrorBoundary>
);
