import React, { useState, useEffect } from 'react';
import { 
  UploadCloud, 
  Search, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  FileText, 
  Download, 
  ArrowRight, 
  Beaker, 
  Info, 
  Lightbulb,
  X
} from 'lucide-react';

// This is a Demo component to visualize the modernized UI in the AI Studio preview.
// The actual modernization is applied to the .html files provided in the project root.

const DemoApp = () => {
  const [step, setStep] = useState('upload'); // 'upload', 'loading', 'results'
  const [fileName, setFileName] = useState('');

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    setStep('loading');
    setTimeout(() => setStep('results'), 2000);
  };

  if (step === 'loading') {
    return (
      <div className="fixed inset-0 bg-slate-900 flex flex-col items-center justify-center text-white p-6 text-center">
        <div className="relative w-24 h-24 mb-8">
          <div className="absolute inset-0 border-4 border-emerald-500/20 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-emerald-500 rounded-full border-t-transparent animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Search className="h-8 w-8 text-emerald-400" />
          </div>
        </div>
        <h2 className="text-2xl font-bold mb-2">Analyzing Label...</h2>
        <p className="text-emerald-200/70 max-w-xs">Our AI is cross-referencing your label with NAFDAC regulatory databases.</p>
      </div>
    );
  }

  if (step === 'results') {
    return (
      <div className="bg-slate-50 min-h-screen pb-20 font-sans">
        <header className="bg-white border-b border-slate-200 py-4 sticky top-0 z-30 shadow-sm">
          <div className="container mx-auto px-4 flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-700 rounded flex items-center justify-center text-white font-bold">N</div>
              <h1 className="font-bold text-emerald-900 hidden md:block">Compliance Analysis</h1>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setStep('upload')} className="text-sm font-medium text-slate-500 hover:text-emerald-600 px-3 py-2 transition-colors">New Analysis</button>
              <button className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-bold px-4 py-2 rounded-lg transition-all flex items-center gap-2">
                <Download className="h-4 w-4" />
                <span>Export Report</span>
              </button>
            </div>
          </div>
        </header>

        <main className="container mx-auto px-4 py-8 max-w-4xl">
          <section className="bg-white rounded-2xl shadow-lg border border-slate-100 p-8 mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Product Name</p>
                <h2 className="text-3xl font-bold text-slate-800">GlowRadiance Serum</h2>
              </div>
              <div className="flex flex-col items-end">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Status</p>
                <span className="inline-flex items-center gap-2 px-6 py-2 bg-rose-100 text-rose-700 rounded-full font-bold text-lg border border-rose-200">
                  <XCircle className="h-6 w-6" />
                  Non-Compliant
                </span>
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="md:col-span-1 space-y-8">
              <section className="bg-white rounded-2xl shadow-md border border-slate-100 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Beaker className="text-emerald-600 h-5 w-5" />
                  <h3 className="font-bold text-slate-800">Ingredients</h3>
                </div>
                <div className="flex flex-wrap gap-2">
                  {['Aqua', 'Glycerin', 'Niacinamide', 'Phenoxyethanol', 'Fragrance'].map(ing => (
                    <span key={ing} className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs border border-slate-200">{ing}</span>
                  ))}
                </div>
              </section>
            </div>

            <div className="md:col-span-2 space-y-8">
              <section className="bg-white rounded-2xl shadow-md border border-rose-100 p-6">
                <div className="flex items-center gap-2 mb-6">
                  <AlertTriangle className="text-rose-600 h-5 w-5" />
                  <h3 className="font-bold text-slate-800">Regulatory Issues</h3>
                </div>
                <div className="space-y-4">
                  <div className="p-4 bg-rose-50 rounded-xl border border-rose-100 flex justify-between items-start gap-4">
                    <p className="text-sm text-rose-900 leading-relaxed">Missing NAFDAC Registration Number placeholder on the primary display panel.</p>
                    <button className="shrink-0 text-[10px] font-bold uppercase tracking-tighter bg-rose-200 text-rose-800 px-2 py-1 rounded">Ref: 12</button>
                  </div>
                </div>
              </section>

              <section className="bg-emerald-900 rounded-2xl shadow-xl p-8 text-white">
                <div className="flex items-center gap-2 mb-6">
                  <FileText className="text-emerald-400 h-6 w-6" />
                  <h3 className="text-xl font-bold">Compliance Directive</h3>
                </div>
                <div className="space-y-4 text-emerald-50/90 leading-relaxed">
                  <p className="text-sm font-medium border-l-2 border-emerald-500/30 pl-4">This label requires immediate corrections before market approval.</p>
                  <div className="flex gap-3 items-start ml-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0"></span>
                    <p className="text-sm">Ensure the manufacturer's full address is legible and includes the country of origin.</p>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="bg-slate-50 text-slate-900 min-h-screen flex flex-col font-sans">
      <header className="bg-white border-b border-slate-200 py-6 sticky top-0 z-10 shadow-sm">
        <div className="container mx-auto px-4 flex flex-col items-center">
          <div className="w-16 h-16 bg-emerald-700 rounded-lg flex items-center justify-center text-white font-bold text-2xl mb-4 shadow-lg">N</div>
          <h1 className="text-2xl md:text-3xl font-bold text-emerald-900 text-center">Label Compliance Checker</h1>
          <p className="text-emerald-600 font-medium tracking-wide uppercase text-xs mt-1">Cosmetics & Household Products</p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-12 max-w-3xl flex-grow">
        <section className="text-center mb-12 animate-in fade-in slide-in-from-bottom-2 duration-700">
          <p className="text-slate-600 text-lg leading-relaxed">
            Upload your product label to verify compliance with <span className="font-semibold text-emerald-700">NAFDAC regulations</span>. 
            Our AI-powered system provides instant regulatory feedback.
          </p>
        </section>

        <section className="bg-white rounded-2xl shadow-xl border border-slate-100 p-8 mb-10 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-100">
          <form onSubmit={handleUpload}>
            <div className="relative group">
              <input 
                type="file" 
                onChange={(e) => setFileName(e.target.files?.[0]?.name || '')}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-20" 
              />
              <div className="bg-emerald-50/30 border-2 border-dashed border-emerald-200 rounded-xl p-12 text-center transition-all duration-300 group-hover:border-emerald-400 group-hover:bg-emerald-50">
                <div className="bg-emerald-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform duration-300">
                  <UploadCloud className="text-emerald-600 h-8 w-8" />
                </div>
                <h3 className="text-lg font-semibold text-slate-800 mb-1">{fileName || 'Select Label File'}</h3>
                <p className="text-slate-500 text-sm">Drag and drop or click to browse</p>
              </div>
            </div>
            <button type="submit" className="w-full mt-8 bg-emerald-700 hover:bg-emerald-800 text-white font-bold py-4 px-6 rounded-xl shadow-lg shadow-emerald-200 transition-all duration-300 flex items-center justify-center gap-2 group">
              <span>Analyze Label</span>
              <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </button>
          </form>
        </section>

        <section className="text-center space-y-4">
          <div className="flex flex-wrap justify-center gap-3">
            {['PNG', 'JPG', 'JPEG', 'PDF'].map(ext => (
              <span key={ext} className="px-3 py-1 bg-slate-200 text-slate-700 rounded-full text-xs font-bold uppercase tracking-wider">{ext}</span>
            ))}
          </div>
          <p className="text-slate-400 text-xs italic">Maximum file size: 10MB • PDF: First page only</p>
        </section>
      </main>

      <footer className="bg-white border-t border-slate-200 py-8 mt-auto">
        <div className="container mx-auto px-4 text-center">
          <p className="text-slate-400 text-sm">Developed by <span className="text-slate-600 font-medium">Babagana, Shamsuddeen</span></p>
        </div>
      </footer>
    </div>
  );
};

export default DemoApp;
