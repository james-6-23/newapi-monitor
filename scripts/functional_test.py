#!/usr/bin/env python3
"""
NewAPI监控系统功能测试脚本
用于验证各个功能模块是否正常工作
"""

import requests
import json
import time
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional


class Colors:
    """终端颜色定义"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


class TestResult:
    """测试结果类"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []

    def add_result(self, test_name: str, status: str, message: str = "", data: Any = None):
        """添加测试结果"""
        self.total += 1
        result = {
            'test_name': test_name,
            'status': status,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.results.append(result)
        
        if status == 'PASS':
            self.passed += 1
            print(f"{Colors.GREEN}[PASS]{Colors.NC} {test_name}: {message}")
        elif status == 'FAIL':
            self.failed += 1
            print(f"{Colors.RED}[FAIL]{Colors.NC} {test_name}: {message}")
        elif status == 'WARN':
            self.warnings += 1
            print(f"{Colors.YELLOW}[WARN]{Colors.NC} {test_name}: {message}")
        else:
            print(f"{Colors.BLUE}[INFO]{Colors.NC} {test_name}: {message}")

    def summary(self):
        """打印测试总结"""
        print("\n" + "="*50)
        print("测试总结")
        print("="*50)
        print(f"总计: {self.total}")
        print(f"{Colors.GREEN}通过: {self.passed}{Colors.NC}")
        print(f"{Colors.RED}失败: {self.failed}{Colors.NC}")
        print(f"{Colors.YELLOW}警告: {self.warnings}{Colors.NC}")
        
        success_rate = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        
        if self.failed == 0:
            print(f"\n{Colors.GREEN}🎉 所有测试通过！{Colors.NC}")
            return True
        else:
            print(f"\n{Colors.RED}❌ 有测试失败，请检查相关功能{Colors.NC}")
            return False


class NewAPIMonitorTester:
    """NewAPI监控系统测试器"""
    
    def __init__(self, base_url: str, timeout: int = 30, verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        self.session.timeout = timeout
        self.result = TestResult()
        
        # 测试时间范围（最近24小时）
        self.end_time = int(time.time() * 1000)
        self.start_time = self.end_time - 24 * 60 * 60 * 1000

    def log_verbose(self, message: str):
        """详细日志输出"""
        if self.verbose:
            print(f"{Colors.BLUE}[DEBUG]{Colors.NC} {message}")

    def make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        self.log_verbose(f"请求: {url}")
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'content': response.text, 'status_code': response.status_code}
                
        except requests.exceptions.RequestException as e:
            self.log_verbose(f"请求失败: {e}")
            return None

    def test_health_check(self):
        """测试健康检查接口"""
        response = self.make_request('/api/health')
        
        if response and response.get('ok'):
            self.result.add_result(
                'health_check',
                'PASS',
                f"服务健康，版本: {response.get('version', 'unknown')}"
            )
        else:
            self.result.add_result(
                'health_check',
                'FAIL',
                "健康检查失败"
            )

    def test_series_api(self):
        """测试时序数据接口"""
        params = {
            'start_ms': self.start_time,
            'end_ms': self.end_time,
            'slot_sec': 3600  # 1小时粒度
        }
        
        response = self.make_request('/api/stats/series', params)
        
        if response and 'data' in response:
            data_points = response.get('total_points', 0)
            if data_points > 0:
                self.result.add_result(
                    'series_api',
                    'PASS',
                    f"获取到 {data_points} 个数据点"
                )
            else:
                self.result.add_result(
                    'series_api',
                    'WARN',
                    "接口正常但无数据"
                )
        else:
            self.result.add_result(
                'series_api',
                'FAIL',
                "时序数据接口异常"
            )

    def test_top_api(self):
        """测试TopN接口"""
        test_cases = [
            {'by': 'user', 'metric': 'tokens'},
            {'by': 'token', 'metric': 'reqs'},
            {'by': 'model', 'metric': 'quota_sum'},
            {'by': 'channel', 'metric': 'tokens'}
        ]
        
        for case in test_cases:
            params = {
                'start_ms': self.start_time,
                'end_ms': self.end_time,
                'by': case['by'],
                'metric': case['metric'],
                'limit': 10
            }
            
            response = self.make_request('/api/stats/top', params)
            
            if response and 'data' in response:
                data_count = len(response['data'])
                self.result.add_result(
                    f'top_api_{case["by"]}_{case["metric"]}',
                    'PASS',
                    f"获取到 {data_count} 条记录"
                )
            else:
                self.result.add_result(
                    f'top_api_{case["by"]}_{case["metric"]}',
                    'FAIL',
                    f"TopN接口异常 (by={case['by']}, metric={case['metric']})"
                )

    def test_anomalies_api(self):
        """测试异常检测接口"""
        rules = ['burst', 'multi_user_token', 'ip_many_users', 'big_request']
        
        for rule in rules:
            params = {
                'start_ms': self.start_time,
                'end_ms': self.end_time,
                'rule': rule
            }
            
            response = self.make_request('/api/stats/anomalies', params)
            
            if response and 'data' in response:
                anomaly_count = response.get('total_count', 0)
                self.result.add_result(
                    f'anomalies_api_{rule}',
                    'PASS',
                    f"检测到 {anomaly_count} 个异常"
                )
            else:
                self.result.add_result(
                    f'anomalies_api_{rule}',
                    'FAIL',
                    f"异常检测接口异常 (rule={rule})"
                )

    def test_frontend_pages(self):
        """测试前端页面"""
        pages = [
            ('/', '主页'),
            ('/dashboard', '总览页'),
            ('/top', 'Top排行页'),
            ('/heatmap', '热力图页'),
            ('/anomalies', '异常中心页')
        ]
        
        for path, name in pages:
            response = self.make_request(path)
            
            if response:
                if 'content' in response and 'html' in response['content'].lower():
                    self.result.add_result(
                        f'frontend_{path.replace("/", "_") or "home"}',
                        'PASS',
                        f"{name}可访问"
                    )
                else:
                    self.result.add_result(
                        f'frontend_{path.replace("/", "_") or "home"}',
                        'WARN',
                        f"{name}返回非HTML内容"
                    )
            else:
                self.result.add_result(
                    f'frontend_{path.replace("/", "_") or "home"}',
                    'FAIL',
                    f"{name}不可访问"
                )

    def test_performance(self):
        """测试性能"""
        # 测试API响应时间
        start_time = time.time()
        response = self.make_request('/api/stats/series', {
            'start_ms': self.start_time,
            'end_ms': self.end_time,
            'slot_sec': 300
        })
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        if response:
            if response_time < 5000:
                self.result.add_result(
                    'performance_api_response',
                    'PASS',
                    f"API响应时间: {response_time:.0f}ms (优秀)"
                )
            elif response_time < 10000:
                self.result.add_result(
                    'performance_api_response',
                    'WARN',
                    f"API响应时间: {response_time:.0f}ms (一般)"
                )
            else:
                self.result.add_result(
                    'performance_api_response',
                    'FAIL',
                    f"API响应时间: {response_time:.0f}ms (较慢)"
                )
        else:
            self.result.add_result(
                'performance_api_response',
                'FAIL',
                "API响应超时或失败"
            )

    def test_data_consistency(self):
        """测试数据一致性"""
        # 获取时序数据
        series_response = self.make_request('/api/stats/series', {
            'start_ms': self.start_time,
            'end_ms': self.end_time,
            'slot_sec': 3600
        })
        
        # 获取TopN数据
        top_response = self.make_request('/api/stats/top', {
            'start_ms': self.start_time,
            'end_ms': self.end_time,
            'by': 'user',
            'metric': 'tokens',
            'limit': 50
        })
        
        if series_response and top_response:
            # 计算时序数据总和
            series_total = sum(item.get('tokens', 0) for item in series_response.get('data', []))
            
            # 计算TopN数据总和
            top_total = sum(item.get('tokens', 0) for item in top_response.get('data', []))
            
            if series_total > 0 and top_total > 0:
                # 允许一定的误差（因为可能有数据更新）
                ratio = abs(series_total - top_total) / max(series_total, top_total)
                if ratio < 0.1:  # 10%误差范围内
                    self.result.add_result(
                        'data_consistency',
                        'PASS',
                        f"数据一致性良好 (时序总计: {series_total}, TopN总计: {top_total})"
                    )
                else:
                    self.result.add_result(
                        'data_consistency',
                        'WARN',
                        f"数据存在差异 (时序总计: {series_total}, TopN总计: {top_total})"
                    )
            else:
                self.result.add_result(
                    'data_consistency',
                    'WARN',
                    "无足够数据进行一致性检查"
                )
        else:
            self.result.add_result(
                'data_consistency',
                'FAIL',
                "无法获取数据进行一致性检查"
            )

    def run_all_tests(self):
        """运行所有测试"""
        print("开始功能测试...")
        print(f"测试目标: {self.base_url}")
        print(f"测试时间范围: {datetime.fromtimestamp(self.start_time/1000)} - {datetime.fromtimestamp(self.end_time/1000)}")
        print("="*50)
        
        # 执行各项测试
        self.test_health_check()
        self.test_series_api()
        self.test_top_api()
        self.test_anomalies_api()
        self.test_frontend_pages()
        self.test_performance()
        self.test_data_consistency()
        
        # 输出结果
        return self.result.summary()


def main():
    parser = argparse.ArgumentParser(description='NewAPI监控系统功能测试')
    parser.add_argument('--url', default='http://localhost', help='API基础URL')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间（秒）')
    parser.add_argument('--verbose', action='store_true', help='显示详细信息')
    parser.add_argument('--output', help='输出测试结果到JSON文件')
    
    args = parser.parse_args()
    
    # 创建测试器并运行测试
    tester = NewAPIMonitorTester(args.url, args.timeout, args.verbose)
    success = tester.run_all_tests()
    
    # 保存测试结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(tester.result.results, f, ensure_ascii=False, indent=2)
        print(f"\n测试结果已保存到: {args.output}")
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
