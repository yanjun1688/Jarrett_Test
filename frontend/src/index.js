import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import App from './App';
import Login from './components/Login';
import ProtectedRoute from './components/ProtectedRoute';
import ProjectList from './components/ProjectList';
import ProjectDetail from './components/ProjectDetail';
import TestCaseList from './components/TestCaseList';
import TestExecutionList from './components/TestExecutionList';
import TestReportList from './components/TestReportList';
import TestScriptList from './components/TestScriptList';
import ApiRequestTester from './components/ApiRequestTester';
import RequestCollectionManager from './components/RequestCollectionManager';
import FeatureTestCaseManager from './components/FeatureTestCaseManager';
import YamlConfigUploaderSimple from './components/YamlConfigUploaderSimple';
import AiTestCaseAnalysis from './components/AiTestCaseAnalysis';
import { AuthProvider } from './context/AuthContext';
import 'antd/dist/reset.css';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<App />}>
            <Route index element={
              <ProtectedRoute>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minHeight: '400px' }}>
                  <div style={{ flex: 1 }}>
                    <h2>欢迎使用测试平台</h2>
                    <p>请从左侧菜单选择一个模块开始。</p>
                  </div>
                  <div style={{ flex: 1, textAlign: 'center' }}>
                    <img
                      src="https://upload.wikimedia.org/wikipedia/en/f/fa/Keith_Jarrett_Koln_Concert_Cover.jpg"
                      alt="测试平台"
                      style={{ maxWidth: '80%', height: 'auto', borderRadius: '8px', boxShadow: '0 4px 8px rgba(0,0,0,0.1)' }}
                    />
                  </div>
                </div>
              </ProtectedRoute>
            } />
            <Route path="projects" element={<ProtectedRoute><ProjectList /></ProtectedRoute>} />
            <Route path="projects/:id" element={<ProtectedRoute><ProjectDetail /></ProtectedRoute>} />
            <Route path="testcases" element={<ProtectedRoute><TestCaseList /></ProtectedRoute>} />
            <Route path="executions" element={<ProtectedRoute><TestExecutionList /></ProtectedRoute>} />
            <Route path="reports" element={<ProtectedRoute><TestReportList /></ProtectedRoute>} />
            <Route path="test-scripts" element={<ProtectedRoute><TestScriptList /></ProtectedRoute>} />
            <Route path="api-tester" element={<ProtectedRoute><ApiRequestTester /></ProtectedRoute>} />
            <Route path="request-collections" element={<ProtectedRoute><RequestCollectionManager /></ProtectedRoute>} />
            <Route path="request-collections/yaml-upload" element={<ProtectedRoute><YamlConfigUploaderSimple /></ProtectedRoute>} />
            <Route path="feature-tests" element={<ProtectedRoute><FeatureTestCaseManager /></ProtectedRoute>} />
            <Route path="ai-test-analysis" element={<ProtectedRoute><AiTestCaseAnalysis /></ProtectedRoute>} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  </React.StrictMode>
);