import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Modal,
  Input,
  Button,
  Space,
  Typography,
  Card,
  List,
  Tag,
  message,
  Spin,
  Row,
  Col,
} from 'antd';
import { SearchOutlined, CheckOutlined } from '@ant-design/icons';
import { uiTestsAPI } from '../api/uiTests';
import BrowserViewer from './BrowserViewer';

const { Text } = Typography;

/**
 * 元素选择器模态框组件
 * 
 * @param {object} props
 * @param {boolean} props.visible - 是否可见
 * @param {function} props.onCancel - 取消回调
 * @param {function} props.onSelect - 选择回调 (locator) => void
 * @param {string} props.initialUrl - 初始URL（可选）
 */
const ElementPickerModal = ({
  visible,
  onCancel,
  onSelect,
  initialUrl = '',
}) => {
  const [url, setUrl] = useState(initialUrl);
  const [loading, setLoading] = useState(false);
  const [screenshotData, setScreenshotData] = useState(null);
  const [currentUrl, setCurrentUrl] = useState(null);
  const [pageTitle, setPageTitle] = useState(null);
  const [elementSelectMode, setElementSelectMode] = useState(false);
  const [selectedElement, setSelectedElement] = useState(null);
  const [selectedLocatorIndex, setSelectedLocatorIndex] = useState(0);
  const [highlightRect, setHighlightRect] = useState(null);
  
  // 使用 ref 存储 props，避免依赖变化导致回调重新创建
  const onCancelRef = useRef(onCancel);
  const initialUrlRef = useRef(initialUrl);
  const prevVisibleRef = useRef(visible);
  
  // 更新 ref 的值（不触发重新渲染）
  useEffect(() => {
    onCancelRef.current = onCancel;
    initialUrlRef.current = initialUrl;
  }, [onCancel, initialUrl]);

  // 加载页面预览
  const handleLoadPage = useCallback(async () => {
    if (!url || !url.trim()) {
      message.warning('请输入URL');
      return;
    }

    setLoading(true);
    setScreenshotData(null);
    setSelectedElement(null);
    setHighlightRect(null);
    setElementSelectMode(false);

    try {
      const response = await uiTestsAPI.previewPage({
        url: url.trim(),
        browser_type: 'chromium',
        viewport_width: 1280,
        viewport_height: 720,
      });

      if (response.data.success) {
        setScreenshotData(response.data.screenshot);
        setCurrentUrl(response.data.url);
        setPageTitle(response.data.title);
        setElementSelectMode(true); // 自动开启元素选择模式
        message.success('页面加载成功，点击页面选择元素');
      } else {
        message.error(response.data.error || '加载页面失败');
      }
    } catch (err) {
      message.error(err.response?.data?.error || err.message || '加载页面失败');
    } finally {
      setLoading(false);
    }
  }, [url]);

  // 处理元素选择（点击Canvas）
  const handleElementClick = useCallback(
    async (eventData) => {
      if (!elementSelectMode || !currentUrl || loading) return;

      const { x, y } = eventData;
      setLoading(true);

      try {
        const response = await uiTestsAPI.selectElement({
          url: currentUrl,
          x,
          y,
          browser_type: 'chromium',
          viewport_width: 1280,
          viewport_height: 720,
        });

        if (response.data.success) {
          const elementInfo = response.data.element_info;
          const candidates = response.data.candidates || [];
          
          setSelectedElement({
            ...response.data,
            clickX: x,
            clickY: y,
          });

          // 设置高亮矩形
          if (elementInfo.rect) {
            setHighlightRect(elementInfo.rect);
          }

          // 默认选择第一个候选（优先级最高的）
          if (candidates.length > 0) {
            setSelectedLocatorIndex(0);
          }

          message.success(`找到元素: ${elementInfo.tag}${elementInfo.id ? '#' + elementInfo.id : ''}`);
        } else {
          message.error(response.data.error || '选择元素失败');
        }
      } catch (err) {
        message.error(err.response?.data?.error || err.message || '选择元素失败');
      } finally {
        setLoading(false);
      }
    },
    [elementSelectMode, currentUrl, loading]
  );

  // 确认选择
  const handleConfirm = useCallback(() => {
    if (!selectedElement || !selectedElement.candidates || selectedElement.candidates.length === 0) {
      message.warning('请先选择一个元素');
      return;
    }

    const selectedCandidate = selectedElement.candidates[selectedLocatorIndex];
    if (onSelect) {
      onSelect({
        locator_type: selectedCandidate.locator_type,
        locator_value: selectedCandidate.locator_value,
        selector: selectedCandidate.selector,
      });
    }
  }, [selectedElement, selectedLocatorIndex, onSelect]);

  // 重置状态（内部使用，不调用 onCancel）
  const resetState = useCallback(() => {
    const currentInitialUrl = initialUrlRef.current;
    setUrl(currentInitialUrl);
    setScreenshotData(null);
    setCurrentUrl(null);
    setPageTitle(null);
    setElementSelectMode(false);
    setSelectedElement(null);
    setSelectedLocatorIndex(0);
    setHighlightRect(null);
  }, []); // 空依赖数组，使用 ref 访问最新值
  
  // 用户点击取消按钮时的处理（需要调用父组件的 onCancel）
  const handleCancel = useCallback(() => {
    resetState();
    // 调用父组件的 onCancel
    if (onCancelRef.current) {
      onCancelRef.current();
    }
  }, [resetState]); // 只依赖 resetState（稳定的）

  // 当visible变化时，如果有initialUrl则自动加载
  useEffect(() => {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/33c73be7-f549-4165-9b71-45c0898325e9',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'ElementPickerModal.js:useEffect_visible',message:'visible useEffect 触发',data:{visible,prevVisible:prevVisibleRef.current,initialUrl:initialUrlRef.current},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
    
    const wasVisible = prevVisibleRef.current;
    const isNowVisible = visible;
    
    if (isNowVisible && !wasVisible) {
      // Modal 打开时，如果有 initialUrl 则设置 URL
      const currentInitialUrl = initialUrlRef.current;
      if (currentInitialUrl && currentInitialUrl.trim()) {
        setUrl(currentInitialUrl);
      }
    } else if (!isNowVisible && wasVisible) {
      // Modal 关闭时，重置状态（使用 resetState，不调用 onCancel）
      resetState();
    }
    
    prevVisibleRef.current = visible;
  }, [visible, resetState]); // 依赖 visible 和 resetState（resetState 是稳定的）

  return (
    <Modal
      title="元素选择器"
      open={visible}
      onCancel={handleCancel}
      width="90%"
      className="element-picker-modal"
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          取消
        </Button>,
        <Button
          key="confirm"
          type="primary"
          disabled={!selectedElement}
          onClick={handleConfirm}
        >
          确认选择
        </Button>,
      ]}
    >
      <Spin spinning={loading}>
        <Space direction="vertical" size="large" className="element-picker-container">
          {/* URL输入和加载 */}
          <Space.Compact className="element-picker-input-group">
            <Input
              placeholder="请输入要预览的URL，例如: https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onPressEnter={handleLoadPage}
              size="large"
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleLoadPage}
              loading={loading}
              size="large"
            >
              加载页面
            </Button>
          </Space.Compact>

          {/* 页面信息 */}
          {currentUrl && (
            <div>
              <Text strong>当前页面: </Text>
              <Text>{currentUrl}</Text>
              {pageTitle && (
                <>
                  <Text strong className="element-picker-title-text">
                    标题:{' '}
                  </Text>
                  <Text>{pageTitle}</Text>
                </>
              )}
            </div>
          )}

          {/* 元素选择模式提示 */}
          {elementSelectMode && !selectedElement && (
            <Card size="small" className="element-picker-hint-card">
              <Text>
                <Text strong>提示：</Text> 点击页面中的元素进行选择
              </Text>
            </Card>
          )}

          <Row gutter={16}>
            {/* 左侧：页面预览 */}
            <Col span={selectedElement ? 16 : 24}>
              <div className="element-picker-viewer-container">
                {screenshotData ? (
                  <div className="element-picker-viewer-container">
                    <BrowserViewer
                      screenshotData={screenshotData}
                      onMouseEvent={(eventData) => {
                        if (eventData.event_type === 'click' && elementSelectMode) {
                          handleElementClick(eventData);
                        }
                      }}
                    />
                    
                    {/* 高亮选中元素的覆盖层 */}
                    {highlightRect && (
                      <div
                        className="element-picker-highlight-overlay"
                        style={{
                          left: `${(highlightRect.x / 1280) * 100}%`,
                          top: `${(highlightRect.y / 720) * 100}%`,
                          width: `${(highlightRect.width / 1280) * 100}%`,
                          height: `${(highlightRect.height / 720) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                ) : (
                  <Card className="element-picker-loading-container">
                    <Text type="secondary">
                      {url
                        ? '点击"加载页面"按钮预览页面'
                        : '请输入URL并加载页面'}
                    </Text>
                  </Card>
                )}
              </div>
            </Col>

            {/* 右侧：元素信息和定位器候选 */}
            {selectedElement && (
              <Col span={8}>
                <Space direction="vertical" size="middle" className="element-picker-info-section">
                  <Card size="small" title="元素信息">
                    <Space direction="vertical" size="small" className="element-picker-element-section">
                      <div>
                        <Text strong>标签: </Text>
                        <Tag>{selectedElement.element_info.tag}</Tag>
                      </div>
                      {selectedElement.element_info.id && (
                        <div>
                          <Text strong>ID: </Text>
                          <Text code>{selectedElement.element_info.id}</Text>
                        </div>
                      )}
                      {selectedElement.element_info.className && (
                        <div>
                          <Text strong>Class: </Text>
                          <Text code className="element-picker-classname-code">
                            {selectedElement.element_info.className.substring(0, 50)}
                            {selectedElement.element_info.className.length > 50 ? '...' : ''}
                          </Text>
                        </div>
                      )}
                      {selectedElement.element_info.textContent && (
                        <div>
                          <Text strong>文本: </Text>
                          <Text>{selectedElement.element_info.textContent}</Text>
                        </div>
                      )}
                    </Space>
                  </Card>

                  <Card size="small" title="定位器候选">
                    <List
                      size="small"
                      dataSource={selectedElement.candidates || []}
                      renderItem={(item, index) => (
                        <List.Item
                          className={`element-picker-locator-item ${index === selectedLocatorIndex ? 'element-picker-locator-item-selected' : ''}`}
                          onClick={() => setSelectedLocatorIndex(index)}
                        >
                          <Space direction="vertical" size="small" className="element-picker-element-section">
                            <Space>
                              {index === selectedLocatorIndex && (
                                <CheckOutlined className="element-picker-check-icon" />
                              )}
                              <Tag color={index === selectedLocatorIndex ? 'blue' : 'default'}>
                                {item.locator_type}
                              </Tag>
                              <Text strong>{item.description}</Text>
                            </Space>
                            <Text code className="element-picker-locator-code">
                              {item.selector}
                            </Text>
                            <Text type="secondary" className="element-picker-locator-secondary">
                              值: {item.locator_value}
                            </Text>
                          </Space>
                        </List.Item>
                      )}
                    />
                  </Card>

                  <Card size="small">
                    <Space direction="vertical" size="small" className="element-picker-element-section">
                      <Text strong>已选择定位器:</Text>
                      {selectedElement.candidates && selectedElement.candidates[selectedLocatorIndex] && (
                        <>
                          <Text>
                            类型:{' '}
                            <Tag color="blue">
                              {selectedElement.candidates[selectedLocatorIndex].locator_type}
                            </Tag>
                          </Text>
                          <Text code className="element-picker-selector-code">
                            {selectedElement.candidates[selectedLocatorIndex].selector}
                          </Text>
                        </>
                      )}
                    </Space>
                  </Card>
                </Space>
              </Col>
            )}
          </Row>
        </Space>
      </Spin>
    </Modal>
  );
};

export default ElementPickerModal;
