package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.Sample;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface SampleMapper extends BaseMapper<Sample> {

    int insertSample(Sample sample);

    int deleteBefore(@Param("cutoff") LocalDateTime cutoff);

    List<Sample> latest(@Param("limit") int limit);
}
