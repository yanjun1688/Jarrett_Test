import React, { useState, useEffect, useCallback } from 'react';
import { Tooltip } from 'antd';
import { ReloadOutlined, DatabaseOutlined } from '@ant-design/icons';
import { chatbotAPI } from '../api';
import './CacheStatsPanel.css';

/**
 * 上下文缓存统计面板
 * 展示温区/冷区摘要缓存的命中与未命中情况
 */
const CacheStatsPanel = ({ visible = true }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const res = await chatbotAPI.getCacheStats();
      if (res.data?.success) {
        setStats(res.data.data);
      }
    } catch {
      // 静默失败
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (visible) fetchStats();
  }, [visible, fetchStats]);

  // 每次发消息后自动刷新（通过 visible 变化触发）
  useEffect(() => {
    if (!visible) return;
    const timer = setInterval(fetchStats, 15000);
    return () => clearInterval(timer);
  }, [visible, fetchStats]);

  if (!visible || !stats) return null;

  const warmTotal = stats.warm_hits + stats.warm_misses;
  const coldTotal = stats.cold_hits + stats.cold_misses;
  const totalHits = stats.warm_hits + stats.cold_hits;
  const totalMisses = stats.warm_misses + stats.cold_misses;
  const totalAll = totalHits + totalMisses;

  const fmtRate = (rate) => `${(rate * 100).toFixed(1)}%`;

  return (
    <div className="cache-stats-panel">
      <div className="cache-stats-header">
        <span className="cache-stats-title">
          <DatabaseOutlined /> 上下文缓存
        </span>
        <Tooltip title="刷新">
          <ReloadOutlined
            className={`cache-stats-refresh ${loading ? 'spinning' : ''}`}
            onClick={fetchStats}
          />
        </Tooltip>
      </div>

      <div className="cache-stats-summary">
        <span className="cache-stats-total">{totalAll} 次请求</span>
        {totalAll > 0 && (
          <span className="cache-stats-rate">
            命中率 {fmtRate(totalAll > 0 ? totalHits / totalAll : 0)}
          </span>
        )}
      </div>

      {totalAll === 0 ? (
        <div className="cache-stats-empty">暂无缓存数据，对话超过10条后生效</div>
      ) : (
        <>
          {/* 温区 */}
          <div className="cache-zone-row">
            <div className="cache-zone-label">
              <span className="zone-dot warm" />温区摘要
            </div>
            <div className="cache-zone-bar-wrap">
              <div className="cache-zone-bar">
                {warmTotal > 0 && stats.warm_hits > 0 && (
                  <Tooltip title={`命中缓存 ${stats.warm_hits} 次`}>
                    <div
                      className="bar-segment hit"
                      style={{ width: `${(stats.warm_hits / warmTotal) * 100}%` }}
                    />
                  </Tooltip>
                )}
                {warmTotal > 0 && stats.warm_misses > 0 && (
                  <Tooltip title={`未命中 ${stats.warm_misses} 次`}>
                    <div
                      className="bar-segment miss"
                      style={{ width: `${(stats.warm_misses / warmTotal) * 100}%` }}
                    />
                  </Tooltip>
                )}
              </div>
            </div>
            <div className="cache-zone-nums">
              <span className="num-hit">{stats.warm_hits}</span>
              <span className="num-sep">/</span>
              <span className="num-miss">{stats.warm_misses}</span>
            </div>
          </div>

          {/* 冷区 */}
          <div className="cache-zone-row">
            <div className="cache-zone-label">
              <span className="zone-dot cold" />冷区摘要
            </div>
            <div className="cache-zone-bar-wrap">
              <div className="cache-zone-bar">
                {coldTotal > 0 && stats.cold_hits > 0 && (
                  <Tooltip title={`命中缓存 ${stats.cold_hits} 次`}>
                    <div
                      className="bar-segment hit"
                      style={{ width: `${(stats.cold_hits / coldTotal) * 100}%` }}
                    />
                  </Tooltip>
                )}
                {coldTotal > 0 && stats.cold_misses > 0 && (
                  <Tooltip title={`未命中 ${stats.cold_misses} 次`}>
                    <div
                      className="bar-segment miss"
                      style={{ width: `${(stats.cold_misses / coldTotal) * 100}%` }}
                    />
                  </Tooltip>
                )}
              </div>
            </div>
            <div className="cache-zone-nums">
              <span className="num-hit">{stats.cold_hits}</span>
              <span className="num-sep">/</span>
              <span className="num-miss">{stats.cold_misses}</span>
            </div>
          </div>

          {/* 图例 */}
          <div className="cache-stats-legend">
            <span><span className="legend-dot hit" />命中</span>
            <span><span className="legend-dot miss" />未命中</span>
            <span>缓存会话: {stats.cached_sessions}</span>
          </div>
        </>
      )}
    </div>
  );
};

export default CacheStatsPanel;
