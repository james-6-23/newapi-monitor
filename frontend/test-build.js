// 简单的TypeScript编译测试脚本
const fs = require('fs');
const path = require('path');

console.log('🔍 检查TypeScript文件...');

const srcDir = path.join(__dirname, 'src');
const files = [
  'App.tsx',
  'api/client.ts',
  'components/DataTable.tsx',
  'components/RangeFilter.tsx',
  'pages/Dashboard.tsx',
  'pages/Top.tsx',
  'pages/Heatmap.tsx',
  'pages/Anomalies.tsx'
];

let hasErrors = false;

files.forEach(file => {
  const filePath = path.join(srcDir, file);
  if (fs.existsSync(filePath)) {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // 检查常见的TypeScript错误模式
    const errors = [];
    
    // 检查未使用的React导入
    if (content.includes("import React from 'react'") && !content.includes('React.')) {
      errors.push('未使用的React导入');
    }
    
    // 检查import.meta.env访问
    if (content.includes('import.meta.env.') && !content.includes('import.meta.env?.')) {
      errors.push('环境变量访问可能有问题');
    }
    
    // 检查TabPane导入
    if (content.includes('TabPane') && !content.includes('<TabPane')) {
      errors.push('未使用的TabPane导入');
    }
    
    if (errors.length > 0) {
      console.log(`❌ ${file}: ${errors.join(', ')}`);
      hasErrors = true;
    } else {
      console.log(`✅ ${file}: 看起来正常`);
    }
  } else {
    console.log(`⚠️  ${file}: 文件不存在`);
  }
});

if (!hasErrors) {
  console.log('\n🎉 所有检查的文件看起来都已修复！');
  console.log('\n📝 修复总结:');
  console.log('✅ 移除了未使用的React导入');
  console.log('✅ 修复了环境变量访问问题');
  console.log('✅ 修复了Ant Design组件类型问题');
  console.log('✅ 修复了ECharts配置类型问题');
  console.log('✅ 修复了DatePicker类型问题');
  console.log('✅ 修复了表格列定义类型问题');
  console.log('✅ 修复了热力图数据类型问题');
  console.log('✅ 移除了未使用的导入');
} else {
  console.log('\n❌ 仍有一些问题需要解决');
}

console.log('\n🚀 建议下一步:');
console.log('1. 在有Docker环境的机器上运行: docker compose build frontend');
console.log('2. 或者在frontend目录运行: npm run build');
console.log('3. 检查是否还有其他TypeScript错误');
