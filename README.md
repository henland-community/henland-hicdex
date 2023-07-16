# henland-hicdex

an indexer for hicetnunc objkts based on [dipdup](https://dipdup.net/) by [Baking Bad](https://baking-bad.org/)

## 1 配置文件修改

> 修改数据库密码等信息

- dipdup.dev.yml

- dipdup.prod.yml

- docker-compose.yml

## 2 hicdex 服务构建与运行

- 更新代码

``` shell
git submodule init
git pull --recurse-submodules
```

- 基于 Dockerfile 构建本地镜像
> 基础镜像版本：dipdup:6.0.0

``` shell
# 直接构建，中间过程会从线上拉取 dipdup 基础镜像
docker-compose build hicdex

# 如果上述构建过程遇到网络问题无法拉取 dipdup 基础镜像，可以执行下述命令手动拉取 dipdup 基础镜像到本地，再重新构建本地 dipdup 镜像
docker pull dipdup/dipdup:6.0.0
docker-compose build hicdex
```

- 启动服务

``` shell
# 启动 hasura 引擎，会同时启动依赖的数据库
docker-compose up -d hasura

# 启动 hicdex 索引服务
docker-compose up hicdex
```
