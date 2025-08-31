import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props){
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error){
    return { hasError: true, error };
  }
  componentDidCatch(error, info){
    // eslint-disable-next-line no-console
    console.error('UI ErrorBoundary caught', error, info);
  }
  render(){
    if(this.state.hasError){
      return <div className="p-4 text-sm text-red-600 bg-red-50 rounded">UI crashed: {String(this.state.error?.message||this.state.error)} <button className="ml-2 underline" onClick={()=>this.setState({hasError:false,error:null})}>Retry</button></div>;
    }
    return this.props.children;
  }
}
