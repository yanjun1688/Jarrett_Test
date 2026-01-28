import React, { lazy, Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import App from './App';
import Login from './components/Login';
import ProtectedRoute from './components/ProtectedRoute';
import LoadingSpinner from './components/LoadingSpinner';
import { AuthProvider } from './context/AuthContext';
import 'antd/dist/reset.css';
import './index.css';

// 路由懒加载 - 按需加载组件
const ProjectList = lazy(() => import('./components/ProjectList'));
const ProjectDetail = lazy(() => import('./components/ProjectDetail'));
const TestCaseList = lazy(() => import('./components/TestCaseList'));
const TestExecutionList = lazy(() => import('./components/TestExecutionList'));
const TestReportList = lazy(() => import('./components/TestReportList'));
const TestScriptList = lazy(() => import('./components/TestScriptList'));
const UiTestManager = lazy(() => import('./components/UiTestManager'));
const ApiRequestTester = lazy(() => import('./components/ApiRequestTester'));
const RequestCollectionManager = lazy(() => import('./components/RequestCollectionManager'));
const FeatureTestCaseManager = lazy(() => import('./components/FeatureTestCaseManager'));
const YamlConfigUploaderSimple = lazy(() => import('./components/YamlConfigUploaderSimple'));
const AiTestCaseAnalysis = lazy(() => import('./components/AiTestCaseAnalysis'));

// 懒加载包装组件，添加Suspense和Loading
const LazyRoute = ({ children }) => (
  <Suspense fallback={<LoadingSpinner />}>
    {children}
  </Suspense>
);

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
            <Route 
              path="projects" 
              element={
                <ProtectedRoute>
                  <LazyRoute><ProjectList /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="projects/:id" 
              element={
                <ProtectedRoute>
                  <LazyRoute><ProjectDetail /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="testcases" 
              element={
                <ProtectedRoute>
                  <LazyRoute><TestCaseList /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="executions" 
              element={
                <ProtectedRoute>
                  <LazyRoute><TestExecutionList /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="reports" 
              element={
                <ProtectedRoute>
                  <LazyRoute><TestReportList /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="test-scripts" 
              element={
                <ProtectedRoute>
                  <LazyRoute><TestScriptList /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="ui-tests" 
              element={
                <ProtectedRoute>
                  <LazyRoute><UiTestManager /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="api-tester" 
              element={
                <ProtectedRoute>
                  <LazyRoute><ApiRequestTester /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="request-collections" 
              element={
                <ProtectedRoute>
                  <LazyRoute><RequestCollectionManager /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="request-collections/yaml-upload" 
              element={
                <ProtectedRoute>
                  <LazyRoute><YamlConfigUploaderSimple /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="feature-tests" 
              element={
                <ProtectedRoute>
                  <LazyRoute><FeatureTestCaseManager /></LazyRoute>
                </ProtectedRoute>
              } 
            />
            <Route 
              path="ai-test-analysis" 
              element={
                <ProtectedRoute>
                  <LazyRoute><AiTestCaseAnalysis /></LazyRoute>
                </ProtectedRoute>
              } 
            />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  </React.StrictMode>
);