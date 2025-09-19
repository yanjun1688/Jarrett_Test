import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import App from './App';
import ProjectList from './components/ProjectList';
import ProjectDetail from './components/ProjectDetail';
import TestCaseList from './components/TestCaseList';
import TestExecutionList from './components/TestExecutionList';
import TestReportList from './components/TestReportList';
import ImportExport from './components/ImportExport';
import TestScriptList from './components/TestScriptList';
import ApiRequestTester from './components/ApiRequestTester';
import RequestCollectionManager from './components/RequestCollectionManager';
import 'antd/dist/reset.css';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <Router>
      <Routes>
        <Route path="/" element={<App />}>
          <Route index element={
            <div>
              <h2>欢迎使用测试平台</h2>
              <p>请从左侧菜单选择一个模块开始。</p>
            </div>
          } />
          <Route path="projects" element={<ProjectList />} />
          <Route path="projects/:id" element={<ProjectDetail />} />
          <Route path="testcases" element={<TestCaseList />} />
          <Route path="executions" element={<TestExecutionList />} />
          <Route path="reports" element={<TestReportList />} />
          <Route path="import-export" element={<ImportExport />} />
          <Route path="test-scripts" element={<TestScriptList />} />
          <Route path="api-tester" element={<ApiRequestTester />} />
          <Route path="request-collections" element={<RequestCollectionManager />} />
        </Route>
      </Routes>
    </Router>
  </React.StrictMode>
);